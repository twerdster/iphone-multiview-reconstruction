'use strict';
const $=id=>document.getElementById(id);
const token=new URLSearchParams(location.hash.slice(1)).get('token')||'';
let photos=[],archive=null,objectUrls=[],running=false,viewer,activeJob=null,activeSummary=null;
try{viewer=new PointViewer($('cloud'));}catch(error){$('progress').textContent=error.message;$('progress').classList.add('error');}
const message=(text,error=false)=>{$('progress').textContent=text;$('progress').classList.toggle('error',error);};
function selection(){
  objectUrls.forEach(URL.revokeObjectURL);objectUrls=[];$('thumbnails').replaceChildren();
  for(const file of photos){const image=document.createElement('img');image.src=URL.createObjectURL(file);objectUrls.push(image.src);image.alt=file.name;$('thumbnails').append(image);}
  $('selection').textContent=archive?`${archive.name} · ${(archive.size/1024/1024).toFixed(1)} MB`:`${photos.length} photographs selected · ${(photos.reduce((s,f)=>s+f.size,0)/1024/1024).toFixed(1)} MB`;
  $('start').disabled=running||!token||(!archive&&photos.length<3);
}
$('photos').addEventListener('change',e=>{archive=null;photos.push(...e.target.files);selection();});
$('camera').addEventListener('change',e=>{archive=null;photos.push(...e.target.files);e.target.value='';selection();});
$('archive').addEventListener('change',e=>{archive=e.target.files[0]||null;photos=[];selection();});
$('clear').addEventListener('click',()=>{photos=[];archive=null;$('photos').value='';$('archive').value='';selection();});
async function api(url,options={}){
  const response=await fetch(url,{...options,headers:{...options.headers,Authorization:`Bearer ${token}`}});
  if(!response.ok){let body;try{body=await response.json();}catch(_){body={};}throw new Error(body.error||`Request failed (${response.status}). Check the server URL and access token.`);}
  return response;
}
function metric(value,label){const div=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');strong.textContent=value;span.textContent=label;div.append(strong,span);return div;}
async function showResult(job,summary,filename="cloud.json"){
  activeJob=job;activeSummary=summary;
  const data=await (await api(`/api/jobs/${job}/${filename}`)).json();const displayed=data.summary;viewer.load(data);$('empty').style.display='none';
  $('metrics').replaceChildren(metric(`${summary.registered_images}/${summary.input_images}`,'registered photographs'),metric(displayed.output_points.toLocaleString(),displayed.output_kind==='sparse_sfm'?'sparse SfM points':'stereo points'),metric(`${summary.mean_reprojection_error_pixels.toFixed(2)} px`,'mean sparse reprojection error'));
  $('downloads').replaceChildren();
  for(const [file,label] of [['result.ply','Final PLY'],['sparse.ply','Sparse PLY'],['summary.json','Run details'],['inputs.json','Input hashes']]){const button=document.createElement('button');button.className='secondary';button.textContent=label;button.addEventListener('click',async()=>{try{const blob=await(await api(`/api/jobs/${job}/${file}`)).blob();const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=file;link.click();setTimeout(()=>URL.revokeObjectURL(url),30000);}catch(error){message(error.message,true);}});$('downloads').append(button);}
  $('model-source').disabled=false;$('model-source').value=filename;$('model-source').options[0].textContent=summary.output_kind==='pairwise_stereo'?'Filtered stereo':'Sparse result';
  message(`Showing ${displayed.output_kind==='pairwise_stereo'?'filtered pairwise stereo':'sparse structure from motion'}. Full run: ${summary.elapsed_seconds.toFixed(1)} s. Sparse reprojection error measures feature fit, not surface accuracy.`);
}
async function poll(job){
  try{
    const state=await(await api(`/api/jobs/${job}`)).json();$('state').textContent=state.state;
    if(state.state==='complete'){running=false;selection();await showResult(job,state.summary);return;}
    if(state.state==='failed')throw new Error(state.message||'Reconstruction failed');
    message(state.message||'Waiting for the reconstruction worker…');setTimeout(()=>poll(job),1000);
  }catch(error){running=false;selection();$('state').textContent='Failed';message(error.message,true);}
}
$('start').addEventListener('click',async()=>{
  running=true;activeJob=null;activeSummary=null;$('model-source').disabled=true;sessionStorage.removeItem('multiview-job');
  $('metrics').replaceChildren();$('downloads').replaceChildren();if(viewer)viewer.count=0;$('empty').style.display='flex';selection();$('state').textContent='Uploading';message('Uploading and checking photographs…');
  try{const body=new FormData();if(archive)body.append('archive',archive);else photos.forEach(file=>body.append('photos',file));const response=await(await api('/api/jobs',{method:'POST',body})).json();sessionStorage.setItem('multiview-job',response.job);poll(response.job);}catch(error){running=false;selection();$('state').textContent='Failed';message(error.message,true);}
});
$('model-source').addEventListener('change',async e=>{if(activeJob){try{await showResult(activeJob,activeSummary,e.target.value);}catch(error){message(error.message,true);}}});
$('reset').addEventListener('click',()=>viewer&&viewer.reset());
$('orbit').addEventListener('click',()=>{if(viewer){viewer.auto=!viewer.auto;$('orbit').textContent=viewer.auto?'Pause rotation':'Auto rotate';}});
$('point-size').addEventListener('input',e=>{if(viewer)viewer.pointSize=Number(e.target.value);});
if(!token){message('Open the complete local URL printed by the server, including its #token= access code.',true);}else{const job=sessionStorage.getItem('multiview-job');if(job){running=true;poll(job);}}
selection();
