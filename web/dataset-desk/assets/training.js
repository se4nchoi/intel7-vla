(() => {
  const el = id => document.getElementById(id);
  const labels = {preparing:'데이터 준비 중', running:'학습 중', completed:'완료', failed:'오류', interrupted:'중단됨'};
  let selected = '', busy = false, starting = false, polling = false, jobs = [], chartJob = null;
  const fmt = n => n == null ? '—' : Number(n).toLocaleString('ko-KR');
  const loss = n => n == null ? '—' : Number(n).toFixed(4);
  async function request(path, body) {
    const response = await fetch('/api/' + path, body === undefined ? {} : {
      method:'POST',headers:{'Content-Type':'application/json','X-LeRobot-Control':'local'},body:JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || '요청을 처리하지 못했습니다.');
    return data;
  }
  async function loadDatasets() {
    const rows = await request('datasets');
    const previous = el('trainingRepo').value || el('datasets')?.value || 'se4nchoi/messi';
    el('trainingRepo').replaceChildren(...rows.map(r => {
      const option = new Option(r.repo,r.repo);
      option.dataset.episodes=r.episodes;option.dataset.frames=r.frames;return option;
    }));
    if (rows.some(r=>r.repo===previous)) el('trainingRepo').value=previous;
    datasetInfo();
  }
  function datasetInfo() {
    const option=el('trainingRepo').selectedOptions[0];
    if (!option) {el('trainingDatasetInfo').textContent='저장된 데이터셋이 없습니다.'; return;}
    const episodes=Number(option.dataset.episodes), ratio=Number(el('trainingSplit').value);
    const valid=ratio ? Math.ceil(episodes*ratio) : 0;
    el('trainingDatasetInfo').textContent=`${fmt(episodes)}개 에피소드 · ${fmt(option.dataset.frames)}프레임 / 학습 ${episodes-valid}개 · 검증 ${valid}개`;
  }
  function controls() {
    el('trainingFields').disabled=busy||starting;
    el('trainingStart').textContent=starting?'학습 시작 요청 중…':'학습 시작';
    el('trainingStartHint').textContent=busy?'실행 중인 학습이 끝나면 새 학습을 시작할 수 있습니다.':
      '시작 전 녹화·저장·추종을 멈춰 주세요. 학습용 복사·검증이 끝나면 추가 수집을 계속할 수 있습니다.';
    el('trainTab').textContent=busy?'학습 ●':'학습';
  }
  function drawChart() {
    const canvas=el('trainingChart');
    if (!canvas.clientWidth) return;
    const ratio=window.devicePixelRatio||1, width=canvas.width=Math.floor(canvas.clientWidth*ratio), height=canvas.height=210*ratio;
    const ctx=canvas.getContext('2d');ctx.clearRect(0,0,width,height);
    const train=chartJob?.losses||[], evaluation=chartJob?.evaluations||[], all=[...train,...evaluation];
    ctx.font=`${11*ratio}px system-ui`;ctx.fillStyle='#91a0b1';
    if (!all.length) {ctx.fillText('학습 스텝이 쌓이면 loss 추이가 표시됩니다.',14*ratio,80*ratio); return;}
    const left=46*ratio, top=12*ratio, right=16*ratio, bottom=26*ratio;
    const maxX=Math.max(1,...all.map(p=>p.step)),maxY=Math.max(.001,...all.map(p=>p.loss))*1.1;
    const x=v=>left+v/maxX*(width-left-right), y=v=>height-bottom-v/maxY*(height-top-bottom);
    ctx.lineWidth=ratio;
    for(let i=0;i<=3;i++) {const value=maxY*i/3,yy=y(value);ctx.strokeStyle='#303944';ctx.beginPath();ctx.moveTo(left,yy);ctx.lineTo(width-right,yy);ctx.stroke();ctx.fillStyle='#91a0b1';ctx.fillText(value.toFixed(2),2*ratio,yy+4*ratio);}
    ctx.fillText('0',left,height-5*ratio);ctx.fillText(fmt(maxX)+' step',Math.max(left,width-100*ratio),height-5*ratio);
    for (const [series,color] of [[train,'#a9ec91'],[evaluation,'#7ec8ef']]) {
      ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1.7*ratio;ctx.beginPath();
      series.forEach((p,i)=>i?ctx.lineTo(x(p.step),y(p.loss)):ctx.moveTo(x(p.step),y(p.loss)));ctx.stroke();
      if (series===evaluation || series.length===1) for (const p of series) {ctx.beginPath();ctx.arc(x(p.step),y(p.loss),3*ratio,0,Math.PI*2);ctx.fill();}
    }
  }
  function render(job) {
    chartJob=job;
    const state=job?.state;
    el('trainingState').textContent=job?(labels[state]||state):'학습 기록 없음';
    el('trainingState').className='pill training-state-'+(state||'idle');
    el('trainingRunLabel').textContent=job?`${job.repo} · ${job.model} · ${fmt(job.episodes)}개 에피소드 · ${fmt(job.frames)}프레임`:'설정을 확인한 뒤 첫 학습을 시작해 주세요.';
    el('trainingStep').textContent=job?`${fmt(job.step)} / ${fmt(job.total_steps)} 스텝`:'학습 대기';
    el('trainingPercent').textContent=(job?.percent||0)+'%';el('trainingProgress').value=job?.percent||0;
    el('trainingLoss').textContent=loss(job?.loss);el('trainingEval').textContent=loss(job?.eval_loss);
    el('trainingETA').textContent=job?.eta||'—';
    el('trainingMessage').textContent=job?.error||job?.message||(state==='completed'?'학습이 완료되었습니다. 체크포인트를 확인해 주세요.':state==='running'?'학습이 진행 중입니다. 예상 시간은 검증·저장 시 달라질 수 있습니다.':'');
    el('trainingMessage').style.color=job?.error?'#ffaea3':'';
    const options=job?.options||{};
    const details=job?[`학습 ID: ${job.id}`,`스텝: ${fmt(job.total_steps)} / 배치: ${options.batch_size??'—'}`,
      `학습률: ${options.learning_rate??'—'} / Warmup: ${options.warmup_steps??'—'}`,
      `검증 비율: ${options.eval_split==null?'—':options.eval_split*100+'%'} / 저장 간격: ${options.save_freq??'—'}`,
      `결과: ${job.output_dir}`,`로그: ${job.log_path}`].join('\n'):'학습 기록 없음';
    el('trainingRunDetails').textContent=details;
    const points=job?.checkpoints||[];el('trainingCheckpointCount').textContent=points.length+'개';
    el('trainingCheckpoints').replaceChildren(...points.map(p=>{const row=document.createElement('div');row.className='checkpoint-row';const title=document.createElement('strong');title.textContent=`${fmt(p.step)} 스텝 · ${(p.bytes/1024/1024).toFixed(0)} MB`;const path=document.createElement('span');path.textContent=p.path;row.append(title,path);return row;}));
    if(!points.length)el('trainingCheckpoints').textContent='저장 간격에 도달하면 모델 경로가 표시됩니다.';
    const log=el('trainingLog'),oldScroll=log.scrollTop;
    log.textContent=job?.log||'아직 출력된 학습 로그가 없습니다.';
    log.scrollTop=el('trainingAutoScroll').checked?log.scrollHeight:oldScroll;
    drawChart();
  }
  async function refresh() {
    if(polling)return;polling=true;
    try {
      const data=await request('training'+(selected?'?'+new URLSearchParams({id:selected}):''));
      jobs=data.jobs;busy=data.busy;
      const select=el('trainingHistory');
      select.replaceChildren(...jobs.map(j=>new Option(`${labels[j.state]||j.state} · ${j.id}`,j.id)));
      if(data.current)select.value=data.current.id;
      if(!jobs.length)select.add(new Option('아직 학습 기록이 없습니다.',''));
      render(data.current);controls();
    } catch(error) {el('trainingState').textContent='상태 확인 실패';el('trainingMessage').textContent=error.message;el('trainingFields').disabled=true;}
    finally {polling=false;}
  }
  el('trainingForm').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||starting)return;
    const number=id=>Number(el(id).value);
    const body={repo:el('trainingRepo').value,steps:number('trainingSteps'),batch_size:number('trainingBatch'),
      num_workers:number('trainingWorkers'),learning_rate:number('trainingLR'),warmup_steps:number('trainingWarmup'),
      eval_split:number('trainingSplit'),save_freq:number('trainingSave'),seed:number('trainingSeed')};
    el('trainingError').textContent='';starting=true;controls();
    try {const data=await request('training-start',body);selected=data.id;await refresh();}
    catch(error) {el('trainingError').textContent=error.message;}
    finally {starting=false;controls();}
  });
  el('trainingHistory').addEventListener('change',()=>{selected=el('trainingHistory').value;refresh();});
  el('trainingRepo').addEventListener('change',datasetInfo);el('trainingSplit').addEventListener('change',datasetInfo);
  window.addEventListener('resize',drawChart);
  window.trainingUI={refresh:async()=>{try{await loadDatasets();}catch(error){el('trainingError').textContent=error.message;}await refresh();},
    show:()=>{drawChart();window.trainingUI.refresh();},
    copyLogs:async()=>{try{await navigator.clipboard.writeText(el('trainingLog').textContent);toast('학습 로그를 복사했습니다.');}catch(error){toast('로그 복사 실패: '+error.message);}}};
  setInterval(()=>{if(!document.hidden)refresh();},5000);
  window.trainingUI.refresh();
  if(location.hash==='#training')tab('train');
})();
