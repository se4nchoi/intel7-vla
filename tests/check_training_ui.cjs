// Execute the shipped training controller against a deterministic DOM and HTTP fixture.
// No browser, GPU job, robot request, or production write is performed.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
class Element {
  constructor(id=''){this.id=id;this.value='';this.children=[];this.listeners={};this.style={};this.dataset={};this.disabled=false;this.textContent='';this.checked=false;this.scrollTop=0;this.scrollHeight=100;this.clientWidth=800;this.className='';}
  replaceChildren(...items){this.children=items;if(this.id==='trainingRepo'||this.id==='trainingHistory')this.value=items[0]?.value||'';}
  append(...items){this.children.push(...items);}
  add(item){this.append(item);}
  get selectedOptions(){return this.children.filter(c=>c.value===this.value);}
  addEventListener(event,callback){this.listeners[event]=callback;}
  getContext(){return new Proxy({}, {get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});}
}
async function main(){
  const html=fs.readFileSync(__dirname+'/../web/dataset-desk/index.html','utf8'),elements={};
  for(const match of html.matchAll(/\bid="([^"]+)"/g))elements[match[1]]=new Element(match[1]);
  const values={trainingRepo:'se4nchoi/messi',trainingSteps:'10000',trainingBatch:'4',trainingLR:'0.0001',trainingWarmup:'1000',trainingSplit:'0.2',trainingSave:'1000',trainingWorkers:'2',trainingSeed:'1000',datasets:'se4nchoi/messi'};
  for(const [key,value] of Object.entries(values))elements[key].value=value;
  elements.trainingAutoScroll.checked=true;
  const get=id=>{assert(elements[id],`Missing element ${id}`);return elements[id]};
  const completed={id:'initial',state:'completed',repo:'se4nchoi/messi',model:'SmolVLA',episodes:10,frames:7840,step:2000,total_steps:2000,percent:100,loss:.11,eval_loss:.098,
    options:{batch_size:4},losses:[{step:10,loss:.5},{step:2000,loss:.11}],evaluations:[{step:2000,loss:.098}],log:'Training complete',checkpoints:[{step:2000,path:'/local/model',bytes:906712520}]};
  let current=completed,busy=false,rejectStart=true,startCalls=[],interval;
  const fetch=async(url,options)=>{
    if(url==='/api/datasets')return {ok:true,json:async()=>[{repo:'se4nchoi/messi',episodes:11,frames:8912}]};
    if(url==='/api/training-start'){
      startCalls.push(JSON.parse(options.body));
      assert.equal(options.headers['X-LeRobot-Control'],'local');
      if(rejectStart)return {ok:false,json:async()=>({error:'녹화를 먼저 멈춰 주세요.'})};
      current={...completed,id:'new-job',state:'preparing',step:0,percent:0,checkpoints:[],log:'복사 중'};busy=true;
      return {ok:true,json:async()=>({ok:true,id:'new-job'})};
    }
    if(url.startsWith('/api/training'))return {ok:true,json:async()=>({current,jobs:[current],busy})};
    throw Error('Unexpected request '+url);
  };
  const context={URLSearchParams,document:{getElementById:get,createElement:()=>new Element(),hidden:false},fetch,
    Option:function(text,value){return Object.assign(new Element(),{textContent:text,value,dataset:{}})},
    window:{devicePixelRatio:1,addEventListener:()=>{}},location:{hash:''},
    navigator:{clipboard:{writeText:async()=>{}}},toast:()=>{},tab:()=>{},
    setInterval:callback=>{interval=callback;},console};
  vm.runInNewContext(fs.readFileSync(__dirname+'/../web/dataset-desk/assets/training.js','utf8'),context);
  await new Promise(setImmediate);await new Promise(setImmediate);
  assert.equal(get('trainingState').textContent,'완료');assert.equal(get('trainingProgress').value,100);
  assert.equal(get('trainingEval').textContent,'0.0980');assert.equal(get('trainingCheckpointCount').textContent,'1개');
  assert.equal(get('trainingFields').disabled,false);assert.match(get('trainingDatasetInfo').textContent,/학습 8개 · 검증 3개/);
  get('trainingSteps').value='20000';
  await get('trainingForm').listeners.submit({preventDefault(){}});
  assert.match(get('trainingError').textContent,/녹화를/);assert.equal(get('trainingFields').disabled,false);
  rejectStart=false;
  await get('trainingForm').listeners.submit({preventDefault(){}});
  assert.equal(startCalls.at(-1).steps,20000);assert.equal(startCalls.at(-1).learning_rate,.0001);
  assert.equal(get('trainingFields').disabled,true);assert.equal(get('trainingState').textContent,'데이터 준비 중');
  const calls=startCalls.length;await get('trainingForm').listeners.submit({preventDefault(){}});assert.equal(startCalls.length,calls);
  current={...current,state:'running',step:100,total_steps:20000,percent:.5,eta:'2:00:00',log:'step 100'};
  await interval();await new Promise(setImmediate);
  assert.equal(get('trainingState').textContent,'학습 중');assert.equal(get('trainingETA').textContent,'2:00:00');
  assert.equal(get('trainingLog').textContent,'step 100');
  console.log('PASS: completed job, progress/loss/checkpoints, 20k parameter submission, recording error, preparing/running polling and duplicate-click prevention.');
}
main().catch(error=>{console.error(error);process.exitCode=1;});
