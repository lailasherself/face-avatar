const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 try{
  const page=await browser.newPage();const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url())&&new URL(r.url()).hostname!=='localhost')external.push(r.url());});
  await page.goto('http://localhost:8014/README.md');
  const report=await page.evaluate(async()=>{
   const {FaceLandmarker,FilesetResolver}=await import('/vendor/mediapipe/vision_bundle.mjs');
   const files=await FilesetResolver.forVisionTasks('/vendor/mediapipe/wasm');
   const face=await FaceLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'/vendor/mediapipe/model/face_landmarker.task',delegate:'CPU'},runningMode:'IMAGE',numFaces:1});
   const model=await(await import('/tongue-model.js')).createTongueModel(),results=[];
   try{
    for(const [name,url] of [['extended','/.context/qa/tongue/foxyface-example.png'],['neutral','/.context/qa/tongue/portrait.jpg']]){
     const image=new Image();image.src=url;await image.decode();const frame=await createImageBitmap(image);
     const detected=face.detect(frame),landmarks=detected.faceLandmarks[0];
     if(!landmarks)throw new Error('No face in '+name);
     const time=performance.now(),score=await model.detect(frame,landmarks);
     results.push({name,score,inferenceMs:performance.now()-time,landmarks:landmarks.length});frame.close();
    }
   }finally{face.close();await model.close();}
   return results;
  });
  console.log(report);assert(report[0].score>.55,'actual tongue image must activate');
  assert(report[1].score<.35,'neutral face must not activate');assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
  fs.writeFileSync('.context/qa/tongue/model-test.json',JSON.stringify({report,errors,external,syntheticScores:false},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
