import { createRequire } from 'node:module';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { mkdirSync, writeFileSync } from 'node:fs';
const require = createRequire(import.meta.url);
const {chromium} = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const here=dirname(fileURLToPath(import.meta.url));
const out=resolve(process.env.DECK_OUT || join(here,'Digital Cat$_strategy_msk.pdf'));
const browser=await chromium.launch({headless:true, executablePath:process.env.CHROMIUM_PATH});
try {
 const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
 await page.goto(pathToFileURL(join(here,'index.html')).href);
 await page.evaluate(()=>document.fonts.ready);
 const slides=page.locator('.slide');
 mkdirSync(join(here,'renders'),{recursive:true});
 for(let i=0;i<await slides.count();i++) {
  await slides.nth(i).screenshot({path:join(here,'renders',`${String(i+1).padStart(2,'0')}.png`)});
 }
 const issues=await page.evaluate(()=>[...document.querySelectorAll('.slide')].flatMap((slide,i)=>{
  const footer=slide.querySelector('footer').getBoundingClientRect();
  if(slide.classList.contains('cover')) return [];
  return [...slide.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().height>0 && el.getBoundingClientRect().bottom>footer.top-2).map(el=>({slide:i+1,text:el.textContent.slice(0,70),bottom:el.getBoundingClientRect().bottom-slide.getBoundingClientRect().top}));
 }));
 if(issues.length) throw new Error(JSON.stringify(issues));
 await page.pdf({path:out,printBackground:true,preferCSSPageSize:true});
 writeFileSync(join(here,'layout-check.json'),JSON.stringify({slides:await slides.count(),footerOverlaps:issues},null,2));
 console.log(JSON.stringify({out,slides:await slides.count(),issues}));
}finally{await browser.close()}
