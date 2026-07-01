
fetch("index.json").then(r=>r.json()).then(idx=>{
 const q=document.getElementById("q"),res=document.getElementById("results");
 function render(list){res.innerHTML=list.slice(0,40).map(i=>
   `<li><a href="${i.u}">${i.t}</a><span class="m">${i.s}</span></li>`).join("");}
 q.addEventListener("input",()=>{const v=q.value.trim().toLowerCase();
   if(!v){res.innerHTML="";return;}
   render(idx.filter(i=>(i.t+" "+i.s).toLowerCase().includes(v)));});
 const p=new URLSearchParams(location.search).get("q");if(p){q.value=p;q.dispatchEvent(new Event("input"));}
});
