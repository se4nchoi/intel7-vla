"""LeRobot hardware connection and live Rerun data loop. One thread owns hardware."""
from collections import deque
import json
import logging
from pathlib import Path
from queue import Queue, Empty
import subprocess
from threading import Lock, Event
import time

import numpy as np
import rerun as rr
import rerun.blueprint as rrb
from camera_address import camera_host

ROOT = Path(__file__).resolve().parent
NAMES = ['shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_roll', 'gripper']
CAMERAS = {'follower_cam':5555,'field_cam':5556}
LABELS = {'connecting':'로봇·카메라 연결 중', 'ready':'연결 완료 · 녹화 대기',
          'recording':'● 실제 녹화 중', 'saving':'영상·관절 데이터 저장 중',
          'error':'연결 또는 기록 오류', 'disconnected':'연결 해제됨', 'closing':'장치 해제 중'}


def blueprint():
    return rrb.Blueprint(rrb.Vertical(
        rrb.Horizontal(*[rrb.Spatial2DView(origin='camera/'+name,name='Camera / '+name) for name in CAMERAS]),
        rrb.Horizontal(rrb.TimeSeriesView(origin='follower',name='Follower joints'),
                       rrb.TimeSeriesView(origin='leader',name='Leader joints'))),
        rrb.TimePanel(timeline='live',play_state='following'))


class Recorder:
    def __init__(self, demo=False, dataset_root=None, teleoperate=False, repo_id='se4nchoi/messi', task='Pick up the red ball, identify the open lane to the left or right of the pickup location, and roll or shoot the ball between the two cones to score a goal.'):
        self.demo = demo
        self.teleoperate = teleoperate
        self.repo_id, self.task = repo_id, task
        self.root = dataset_root or Path.home() / '.cache/huggingface/lerobot/se4nchoi/messi'
        self.lock, self.commands, self.quit = Lock(), Queue(), Event()
        self.data = dict(app='lerobot-rerun-recorder',state='connecting', label=LABELS['connecting'], frames=0, elapsed=0.,
                         fps=0., episodes=0, error='', message='', leader={}, follower={})
        self.robot = self.leader = self.dataset = None
        self.started = 0.
        self.duration = 30.
        self.epoch = time.monotonic()
        if (self.root / 'meta/info.json').exists():
            self.data['episodes'] = json.loads((self.root / 'meta/info.json').read_text())['total_episodes']

    def update(self, **values):
        if 'state' in values:
            values['label'] = LABELS[values['state']]
        with self.lock:
            self.data.update(values)

    def status(self):
        with self.lock:
            return dict(self.data)

    def connect(self):
        self.update(state='connecting', error='')
        if self.demo:
            self.update(state='ready', message='테스트 모드: 실제 로봇·기존 데이터셋을 사용하지 않습니다.')
            return
        from lerobot.cameras.zmq import ZMQCameraConfig
        from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
        from lerobot.robots.so_follower.so_follower import SOFollower
        from lerobot.teleoperators.so_leader import SOLeader, SOLeaderTeleopConfig
        gateway = camera_host()

        class HoldFollower(SOFollower):
            def configure(self):
                # Initialize the hold goal from the real pose before re-enabling torque.
                self.bus.disable_torque()
                pose = self.bus.sync_read('Present_Position', normalize=False)
                self.bus.sync_write('Goal_Position', pose, normalize=False)
                super().configure()

        self.leader = SOLeader(SOLeaderTeleopConfig(id='leader', use_degrees=False,
            port='/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90149145-if00'))
        self.robot = HoldFollower(SOFollowerRobotConfig(id='follower', use_degrees=False,
            max_relative_target=None,
            port='/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B90150163-if00',
            cameras={name:ZMQCameraConfig(server_address=gateway, camera_name=name,port=port,
                                                 width=640,height=480,fps=30) for name,port in CAMERAS.items()}))
        # Never open an interactive calibration prompt from the background service.
        for device in (self.leader, self.robot):
            device.bus.connect(handshake=False)
            # Give the USB serial adapter time to settle after opening the port.
            time.sleep(.2)
            device.bus.port_handler.ser.reset_input_buffer()
            expected = {motor.id:device.bus.model_number_table[motor.model] for motor in device.bus.motors.values()}
            for attempt in range(3):
                found = {motor_id:device.bus.ping(motor_id,num_retry=2) for motor_id in expected}
                if found == expected:
                    break
                time.sleep(.2)
            else:
                raise ConnectionError(f'{device.id}: motor check failed; expected {expected}, found {found}')
            device.bus._assert_same_firmware()
            if not device.calibration or not device.bus.is_calibrated:
                raise RuntimeError(f'{device.id}: 저장된 캘리브레이션과 모터 설정이 다릅니다. 별도 캘리브레이션이 필요합니다.')
        # Setup uses individual acknowledged writes. A dropped USB reply must
        # retry that write rather than aborting the entire connection sequence.
        def configure(device):
            original_write = device.bus.write
            def write_with_retry(*args, **kwargs):
                kwargs['num_retry'] = max(3, kwargs.get('num_retry', 0))
                return original_write(*args, **kwargs)
            device.bus.write = write_with_retry
            try:
                device.configure()
            finally:
                device.bus.write = original_write
        configure(self.leader)
        for camera in self.robot.cameras.values():
            camera.connect()
        configure(self.robot)
        self.leader.get_action()
        self.robot.get_observation()
        self.update(state='ready', message='두 팔과 카메라 연결 완료. 녹화 시작 전 시작 자세를 맞추세요.')

    def open_dataset(self):
        if self.dataset is not None:
            return
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        from lerobot.configs.video import RGBEncoderConfig
        from lerobot.common.control_utils import sanity_check_dataset_robot_compatibility
        from lerobot.scripts.lerobot_record import (aggregate_pipeline_dataset_features,
            create_initial_features, combine_feature_dicts, make_default_processors)
        if not (self.root/'meta/info.json').exists():
            features = {'action':{'dtype':'float32','shape':(6,),'names':[n+'.pos' for n in NAMES]},
                'observation.state':{'dtype':'float32','shape':(6,),'names':[n+'.pos' for n in NAMES]},
                **{'observation.images.'+name:{'dtype':'video','shape':(480,640,3),
                    'names':['height','width','channels'],'info':{'is_depth_map':False}} for name in CAMERAS}}
            self.dataset = LeRobotDataset.create(self.repo_id, fps=30, root=self.root,
                robot_type='so_follower', features=features, use_videos=True,
                rgb_encoder=RGBEncoderConfig(vcodec='h264',preset='ultrafast'), encoder_threads=2,
                image_writer_threads=2)
        else:
            self.dataset = LeRobotDataset.resume(self.repo_id,root=self.root,
                encoder_threads=2,image_writer_threads=4)
            if self.demo:
                return
            t, _, o = make_default_processors()
            features = combine_feature_dicts(
                aggregate_pipeline_dataset_features(pipeline=t,
                    initial_features=create_initial_features(action=self.robot.action_features),use_videos=True),
                aggregate_pipeline_dataset_features(pipeline=o,
                    initial_features=create_initial_features(observation=self.robot.observation_features),use_videos=True))
            sanity_check_dataset_robot_compatibility(self.dataset,self.robot,30,features)

    def save(self, discard=False):
        if self.status()['state'] != 'recording':
            return
        self.update(state='saving')
        if self.status()['frames']:
            if discard:
                self.dataset.clear_episode_buffer()
            else:
                self.dataset.save_episode()
        else:
            self.dataset.clear_episode_buffer()
        # Close parquet writers now so a saved episode is readable immediately.
        self.dataset.finalize()
        self.dataset = None
        self.teleoperate = False
        info = json.loads((self.root / 'meta/info.json').read_text())
        self.update(state='ready', teleoperating=False, episodes=info['total_episodes'],
                    message='이번 녹화를 버렸습니다.' if discard else '영상과 관절 데이터 저장 완료. 다음 녹화를 시작할 수 있습니다.')

    def observe(self):
        if self.demo:
            now = time.monotonic() - self.epoch
            values = {n+'.pos':float(np.sin(now+i)*20) for i,n in enumerate(NAMES)}
            frame = np.zeros((480,640,3),dtype=np.uint8)
            frame[:,:,1] = int((np.sin(now)+1)*100)
            return {**values,**{name:frame.copy() for name in CAMERAS}}, values
        try:
            observation = self.robot.get_observation()
        except Exception as exc:
            try:
                observation = {n+'.pos':self.robot.bus.read('Present_Position',n,num_retry=2) for n in NAMES}
                for name,camera in self.robot.cameras.items():
                    observation[name] = camera.read_latest()
            except Exception as fallback:
                raise ConnectionError(f'Follower read failed: {fallback}') from exc
        try:
            action = self.leader.get_action()
        except Exception as exc:
            try:
                action = {n+'.pos':self.leader.bus.read('Present_Position',n,num_retry=2) for n in NAMES}
            except Exception as fallback:
                raise ConnectionError(f'Leader read failed: {fallback}') from exc
        return observation, action

    def close_devices(self):
        if self.dataset is not None:
            try:
                if self.status()['state'] == 'recording':
                    self.save()
                else:
                    self.dataset.finalize()
            except Exception:
                logging.exception('Dataset finalization failed')
        for device in (self.robot,self.leader):
            if device is None:
                continue
            for camera in getattr(device,'cameras',{}).values():
                if camera.is_connected:
                    try: camera.disconnect()
                    except Exception: logging.exception('Camera disconnect failed')
            if device.bus.is_connected:
                try: device.bus.disconnect(disable_torque=True)
                except Exception:
                    logging.exception('Motor disconnect failed; closing serial handle')
                    device.bus.port_handler.closePort()
        self.robot = self.leader = None
        self.dataset = None

    def run(self):
        rr.send_blueprint(blueprint())
        last_log = 0.
        ticks = deque(maxlen=60)
        read_failures = 0
        follow_origin = None
        follow_start = 0.
        try:
            self.connect()
            self.update(teleoperating=self.teleoperate)
            while not self.quit.is_set():
                tick = time.monotonic()
                ticks.append(tick)
                try:
                    action, payload = self.commands.get_nowait()
                except Empty:
                    action = None
                if action == 'shutdown':
                    if self.status()['state']=='recording': self.save()
                    self.quit.set()
                    break
                if action == 'follow':
                    self.teleoperate = bool(payload['enabled'])
                    self.update(teleoperating=self.teleoperate)
                if action == 'reconnect':
                    self.close_devices()
                    self.connect()
                if action == 'start' and self.status()['state']=='ready':
                    self.open_dataset()
                    self.duration = payload['duration']
                    self.started = time.monotonic()
                    self.update(state='recording',frames=0,elapsed=0.,error='',message='')
                if action in ('stop','discard'):
                    self.save(discard=action=='discard')
                try:
                    obs, leader = self.observe()
                    if read_failures:
                        self.update(message='통신 복구 완료.')
                    read_failures = 0
                except Exception:
                    follow_origin = None
                    read_failures += 1
                    if read_failures > 10:
                        raise
                    logging.warning('Hardware read retry %s/10',read_failures)
                    self.update(message=f'로봇 통신 재시도 중 ({read_failures}/10)')
                    self.quit.wait(.1)
                    continue
                recording = self.status()['state']=='recording'
                sent = leader
                if recording or self.teleoperate:
                    if not self.demo:
                        if follow_origin is None:
                            follow_origin = {n+'.pos':float(obs[n+'.pos']) for n in NAMES}
                            follow_start = time.monotonic()
                        sent = self.robot.send_action(leader)
                        self.update(command=sent,tracking_error_max=max(abs(float(obs[k])-float(leader[k])) for k in leader))
                if recording:
                    from lerobot.utils.feature_utils import build_dataset_frame
                    frame = {**build_dataset_frame(self.dataset.features,obs,prefix='observation'),
                             **build_dataset_frame(self.dataset.features,sent,prefix='action'),
                             'task':self.task}
                    self.dataset.add_frame(frame)
                    elapsed = time.monotonic()-self.started
                    self.update(frames=self.status()['frames']+1,elapsed=elapsed)
                    if elapsed >= self.duration:
                        self.save()
                follower = {n+'.pos':float(obs[n+'.pos']) for n in NAMES}
                self.update(leader=leader,follower=follower)
                if tick-last_log >= 1/15:
                    rr.set_time('live',duration=tick-self.epoch)
                    for name in CAMERAS:
                        rr.log('camera/'+name,rr.Image(obs[name]).compress(jpeg_quality=75))
                    for name in NAMES:
                        rr.log('follower/'+name,rr.Scalars(follower[name+'.pos']))
                        rr.log('leader/'+name,rr.Scalars(leader[name+'.pos']))
                    last_log = tick
                if len(ticks)>1:
                    self.update(fps=(len(ticks)-1)/(ticks[-1]-ticks[0]))
                self.quit.wait(max(0,1/30-(time.monotonic()-tick)))
        except Exception as exc:
            logging.exception('Recorder failed')
            if self.status()['state']=='recording' and self.status()['frames']:
                try: self.save()
                except Exception: logging.exception('Partial episode save failed')
            self.update(state='error',error=str(exc))
        finally:
            self.close_devices()
            if self.quit.is_set():
                self.update(state='disconnected')
