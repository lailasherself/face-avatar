const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage({viewport:{width:512,height:512},deviceScaleFactor:1});
  await page.addInitScript(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Thumbnail render','NotAllowedError');};});
  await page.goto('http://localhost:8014/cockpit.html?qa&assets=3dai');
  await page.waitForFunction(()=>window.fleetQA?.character);
  await page.addStyleTag({content:'#notice,#camera-retry,#loading{display:none!important}'});
  const ids=['orbit','pearl','juno','fuzz','clementine','coral','sprout','atl'];
  fs.mkdirSync('assets/3dai/refined/thumbnails',{recursive:true});
  for(const id of ids){
   await page.evaluate(i=>document.querySelectorAll('.character')[i].click(),ids.indexOf(id));
   await page.waitForFunction(id=>fleetQA.character===id,id);await page.waitForTimeout(800);
   await page.locator('#scene').screenshot({path:`assets/3dai/refined/thumbnails/${id}.png`});
  }
  for(const file of ['assets/3dai/manifest.json','assets/3dai/refined/manifest.json']){
   const backup=path.join('.context/before-no-vehicle',file);fs.mkdirSync(path.dirname(backup),{recursive:true});
   if(!fs.existsSync(backup))fs.copyFileSync(file,backup);
   const manifest=JSON.parse(fs.readFileSync(file,'utf8'));
   for(const c of manifest.characters)c.thumbnail=`assets/3dai/refined/thumbnails/${c.id}.png`;
   fs.writeFileSync(file,JSON.stringify(manifest,null,2)+'\n');
  }
  console.log('Rendered eight standing character thumbnails; originals preserved.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
