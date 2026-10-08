const {chromium}=require('playwright');
const assert=require('node:assert/strict');

(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
  try{
    const page=await browser.newPage(),errors=[];
    page.on('pageerror',error=>errors.push(error.message));
    await page.route('**/tracking-test.html',route=>route.fulfill({contentType:'text/html',body:
      '<script type="importmap">{"imports":{"three":"/vendor/three/three.module.js"}}</script>'}));
    await page.goto(`${process.env.INSTALLATION_URL||'http://localhost:8014'}/tracking-test.html`);
    const results=await page.evaluate(async()=>{
      const {PhotoBooth}=await import('/photo-booth.js');
      const results=[];
      for(const scenario of ['occluded','stale-frame','persistent-loss','other-person','crowd','other-character']){
        let state={ready:true,people:1,person:'visitor',character:'orbit'},fresh=true,captures=0;
        const actions=[];
        if(scenario==='stale-frame')fresh=false;
        else if(scenario==='other-person')state.person='other';
        else if(scenario==='crowd')state.people=2;
        else if(scenario==='other-character')state.character='cosmic';
        else state={...state,ready:false,people:0,person:null};
        const recover=['occluded','stale-frame'].includes(scenario)?setTimeout(()=>{
          state={ready:true,people:1,person:'visitor',character:'orbit'};fresh=true;
        },180):null;
        const booth={state:()=>state,captureReady:()=>fresh,connection:{mode:'cloud'},
          capture:()=>{
            if(!state.ready||!fresh)throw Error('Captured a stale frame');
            captures++;
            const canvas=document.createElement('canvas');canvas.width=320;canvas.height=240;
            return {composite:canvas,name:'Orbit'};
          },request:async action=>actions.push(action)};
        await PhotoBooth.prototype.makePhoto.call(booth,'job','visitor','orbit');
        clearTimeout(recover);results.push({scenario,captures,actions});
      }
      return results;
    });
    for(const result of results){
      const succeeds=['occluded','stale-frame'].includes(result.scenario);
      assert.equal(result.captures,succeeds?1:0,JSON.stringify(result));
      assert.deepEqual(result.actions,[succeeds?'complete':'fail'],JSON.stringify(result));
    }
    assert.deepEqual(errors,[]);
    console.log('PASS shutter recovery, fresh-frame requirement, persistent loss, person/crowd/character guards');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
