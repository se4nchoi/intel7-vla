"""Training integration checks with temporary datasets and a mocked GPU command."""
import _bootstrap  # repository source path, no environment mutation
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from intel7_vla.training import jobs


class TrainingChecks(unittest.TestCase):
    def test_options_and_log_parser(self):
        for body in ({'repo':'../test'}, {'steps':True}, {'steps':12.5},
                     {'learning_rate':float('nan')}, {'command':'rm'},
                     {'steps':100,'warmup_steps':100}, {'num_workers':8}):
            with self.assertRaises(ValueError):
                jobs.validated_options(body)
        self.assertEqual(jobs.validated_options({})['steps'],10000)
        progress=jobs.parse_progress('Training: 25%|xx| 500/2000 [03:00<09:00, 2step/s]\r'
            'INFO step:500 smpl:2K loss:0.25 grdn:4\nINFO step 500: eval_loss=0.3\n')
        self.assertEqual((progress['step'],progress['total_steps'],progress['eta']),(500,2000,'09:00'))
        self.assertEqual(progress['evaluations'][0]['loss'],.3)
        self.assertNotIn('Training:',progress['log'])
        mixed=jobs.parse_progress('Training: 25%|xx| 500/2000 [03:00<09:00, 2step/s]INFO step:500 loss:0.25')
        self.assertIn('step:500 loss:0.25',mixed['log'])
        abbreviated=jobs.parse_progress('Training: 51%|xx| 1020/2000 [03:00<09:00, 2step/s]INFO step:1K loss:0.25')
        self.assertEqual(abbreviated['losses'][0]['step'],1020)

    def test_pid_reuse_and_final_checkpoint(self):
        with tempfile.TemporaryDirectory() as root:
            manager=jobs.TrainingManager(runs=Path(root))
            run=Path(root)/'sample';run.mkdir()
            jobs.write_json(run/'run.json',{'pid':999999,'steps':20,'created':1})
            (run/'train.log').write_text('Training: 100%|xx| 20/20 [00:01<00:00, 20step/s]\n')
            self.assertEqual(manager.describe(run)['state'],'interrupted')
            model=run/'output/checkpoints/last/pretrained_model/model.safetensors'
            model.parent.mkdir(parents=True);model.write_bytes(b'check')
            self.assertEqual(manager.describe(run)['state'],'completed')
            self.assertFalse(jobs.job_process_alive(999999,run,'123'))
            with self.assertRaises(ValueError):manager.folder('../escape')

    def test_launch_records_options_and_rejects_overlap(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);manager=jobs.TrainingManager(runs=root/'runs',cache=root/'cache',lerobot=root/'lerobot')
            source=manager.cache/'local/test';(source/'meta').mkdir(parents=True)
            jobs.write_json(source/'meta/info.json',{'total_episodes':4,'total_frames':100})
            manager.base=root/'base';manager.base.mkdir();(manager.base/'model.safetensors').touch()
            python=manager.lerobot/'.venv/bin/python';python.parent.mkdir(parents=True);python.touch()
            fake=Mock(pid=999998);fake.poll.return_value=None
            with patch.object(jobs.subprocess,'Popen',return_value=fake) as spawn:
                result=manager.start({'repo':'local/test'})
            args=spawn.call_args.args[0]
            self.assertTrue(args[1].endswith('/run_training_job.py'))
            self.assertEqual(jobs.read_json(manager.folder(result['id'])/'run.json')['options']['steps'],10000)
            with patch.object(jobs,'job_process_alive',return_value=True):
                self.assertTrue(manager.preparing())
                with self.assertRaisesRegex(ValueError,'이미'):
                    manager.start({'repo':'local/test'})

    def test_real_snapshot_preparation_without_training(self):
        # Reuse the fixed first-run snapshot; never read/write the live recording tree.
        original=Path.home()/'vla-training/runs/messi-smolvla-20261023-143728/dataset'
        if not original.is_dir():self.skipTest('First-run snapshot not available on this PC')
        with tempfile.TemporaryDirectory(prefix='training-check-') as root:
            root=Path(root);manager=jobs.TrainingManager(runs=root/'runs',cache=root/'cache')
            link=manager.cache/'local/test';link.parent.mkdir(parents=True);link.symlink_to(original,target_is_directory=True)
            run=root/'job';run.mkdir()
            options=jobs.validated_options({'repo':'local/test','steps':20,'warmup_steps':2,'save_freq':10})
            jobs.write_json(run/'run.json',{'options':options})
            with patch.object(jobs,'TrainingManager',return_value=manager), \
                 patch.object(jobs.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as execute:
                jobs.run_job(run)
            args=execute.call_args.args[0]
            self.assertIn('--steps=20',args)
            self.assertIn('--policy.push_to_hub=false',args)
            self.assertTrue((run/'dataset-sha256.json').is_file())
            config=jobs.read_json(run/'base-model/config.json')
            self.assertIn('observation.images.field_cam',config['input_features'])
            self.assertNotIn('observation.images.camera1',config['input_features'])
            self.assertEqual(jobs.read_json(run/'exit.json')['returncode'],0)
            # A real training command is never invoked by this check.
            self.assertEqual(execute.call_count,1)

    def test_http_control_validation(self):
        from intel7_vla.web import server as ui
        ui.DEMO=True
        with tempfile.TemporaryDirectory() as root:
            manager=jobs.TrainingManager(runs=Path(root)/'runs')
            with patch.object(ui,'training',manager):
                server=ThreadingHTTPServer(('127.0.0.1',0),ui.Handler)
                thread=Thread(target=server.serve_forever,daemon=True);thread.start()
                base=f'http://127.0.0.1:{server.server_port}'
                try:
                    with urlopen(base+'/api/training') as response:
                        data=json.load(response)
                    self.assertFalse(data['busy']);self.assertIsNone(data['current'])
                    request=Request(base+'/api/training-start',data=b'{}',method='POST')
                    with self.assertRaises(HTTPError) as err:urlopen(request)
                    self.assertEqual(err.exception.code,400)
                    # Invalid options are rejected before any process can be launched.
                    request=Request(base+'/api/training-start',data=b'{"steps":-1}',method='POST',
                        headers={'X-LeRobot-Control':'local','Content-Type':'application/json'})
                    with self.assertRaises(HTTPError) as err:urlopen(request)
                    self.assertEqual(err.exception.code,400)
                    with urlopen(base+'/training_ui.js') as response:
                        self.assertIn(b'training-start',response.read())
                    with patch.object(ui,'status',return_value={'state':'recording'}), \
                         patch.object(manager,'start') as launch:
                        request=Request(base+'/api/training-start',data=b'{}',method='POST',
                            headers={'X-LeRobot-Control':'local','Content-Type':'application/json'})
                        with self.assertRaises(HTTPError):urlopen(request)
                        launch.assert_not_called()
                finally:
                    server.shutdown();server.server_close();thread.join()


if __name__=='__main__':
    unittest.main(verbosity=2)
