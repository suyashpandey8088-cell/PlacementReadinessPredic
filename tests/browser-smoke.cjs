/* Optional real-browser regression test. See docs/VERCEL.md for tooling/setup. */
const {chromium:pw}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 let options={headless:true};
 if(process.env.BROWSER_EXECUTABLE){options.executablePath=process.env.BROWSER_EXECUTABLE;options.args=['--no-sandbox','--disable-dev-shm-usage'];}
 if(process.env.USE_SPARTICUZ){const c=(await import(require.resolve('@sparticuz/chromium'))).default;options={args:c.args.filter(a=>a!=='--single-process'),executablePath:await c.executablePath(),headless:true};}
 const browser=await pw.launch(options);
 const context=await browser.newContext({viewport:{width:1440,height:1050}});
 const page=await context.newPage(), errors=[];
 page.setDefaultTimeout(60000);
 page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.P2P_BASE_URL||'http://127.0.0.1:5173';
 fs.mkdirSync('.cache/screenshots',{recursive:true});
 async function screen(name){await page.screenshot({path:`.cache/screenshots/${name}.png`,fullPage:true});}
 async function healthy(){if(await page.locator('.error').count())throw new Error(await page.locator('.error').first().innerText());}
 async function nextSection(i){await page.getByRole('button',{name:i===4?'Review my answers':'Save & continue',exact:true}).click();await page.getByText(i===4?'One last look before your results.':`Section ${i+2} of 5`,{exact:false}).waitFor();}
 await page.goto(base);await page.getByRole('heading',{name:'Your preparation.'}).waitFor();await screen('overview');
 await page.getByRole('link',{name:'Assess my readiness',exact:true}).first().click();
 await page.locator('#cgpa').fill('8.2');await nextSection(0);
 await page.locator('#languages').fill('0');await page.getByRole('button',{name:'Save & continue'}).click();await page.getByRole('alert').filter({hasText:'no programming languages'}).waitFor();
 await page.locator('#languages').fill('1');await nextSection(1);await screen('assessment');
 await nextSection(2);await nextSection(3);await nextSection(4);
 await page.getByText('8.2',{exact:true}).waitFor();await screen('review');
 await page.getByRole('button',{name:'Calculate my readiness'}).click();await page.getByRole('heading',{name:'Here’s where you stand.'}).waitFor();await screen('results');
 await healthy();
 await page.getByRole('button',{name:'Save assessment',exact:true}).click();await page.getByRole('button',{name:'Saved on this device'}).waitFor();
 await page.getByRole('link',{name:'My action plan',exact:true}).click();
 await page.getByRole('checkbox',{name:'Mark day 1 complete',exact:true}).check();await page.getByText('1 of 7 days complete',{exact:true}).waitFor();await screen('plan');
 let dlPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download plan · CSV'}).click();let dl=await dlPromise;await dl.saveAs('.cache/plan.csv');
 await page.getByRole('link',{name:'My results',exact:true}).click();await page.getByRole('button',{name:'Update my answers'}).click();
 await page.locator('#cgpa').fill('9');await nextSection(0);
 await page.locator('input[name="dsa"][value="4"]').check();await nextSection(1);await nextSection(2);await nextSection(3);await nextSection(4);
 await page.getByRole('button',{name:'Calculate my readiness'}).click();await page.getByRole('button',{name:'Save assessment',exact:true}).click();await page.getByRole('button',{name:'Saved on this device'}).waitFor();
 await page.getByRole('link',{name:'My progress',exact:true}).click();await page.locator('#trend-chart').waitFor();await screen('progress');
 dlPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Export CSV',exact:true}).click();dl=await dlPromise;await dl.saveAs('.cache/history.csv');
 if(!fs.readFileSync('.cache/history.csv','utf8').includes('readiness_score'))throw Error('CSV headers missing');
 await page.reload();await page.getByRole('heading',{name:'Look at how far you’ve come.'}).waitFor();
 await page.getByRole('link',{name:'Privacy & your data'}).click();
 dlPromise=page.waitForEvent('download');await page.getByRole('button',{name:'JSON backup',exact:true}).click();dl=await dlPromise;await dl.saveAs('.cache/history-backup.json');
 const backup=JSON.parse(fs.readFileSync('.cache/history-backup.json','utf8'));if(backup.assessments.length!==2)throw Error('Expected two genuine saved records');
 await page.locator('#confirm-delete').check();await page.getByRole('button',{name:'Delete my browser data'}).click();
 await page.getByRole('link',{name:'My progress',exact:true}).click();await page.getByRole('heading',{name:'Your starting line is waiting.'}).waitFor();
 await page.getByRole('link',{name:'Privacy & your data'}).click();await page.locator('#restore-file').setInputFiles('.cache/history-backup.json');
 await page.getByText('2 assessment(s) restored.',{exact:false}).waitFor();
 await page.getByRole('link',{name:'My progress',exact:true}).click();await page.locator('#trend-chart').waitFor();
 await page.getByRole('link',{name:'Model insights',exact:true}).click();await page.locator('#class-chart').waitFor();await screen('model');
 await page.getByRole('tab',{name:'Data & workflow'}).click();await page.getByRole('heading',{name:'A leakage-safe workflow'}).waitFor();
 await page.getByRole('tab',{name:'Try the model'}).click();await page.getByRole('button',{name:'Run simulated inference'}).click();await page.getByText('Simulated exercise class:',{exact:false}).waitFor();
 await page.getByRole('link',{name:'About & methodology',exact:true}).click();await page.getByText('Academic preparation · 15% of overall score',{exact:true}).click();await screen('about');
 // Optional-account routes while signed out (works whether accounts are configured or not).
 await page.goto(base+'/login');await page.locator('#main h1').waitFor();await screen('login');
 const authHeading=await page.locator('#main h1').innerText();
 const authConfigured=await page.locator('#auth-form').count();
 if(authConfigured){
   if(!authHeading.includes('Welcome back'))throw Error('Unexpected configured sign-in heading: '+authHeading);
   await page.getByRole('tab',{name:'Create account'}).click();await page.getByRole('heading',{name:'Create your account'}).waitFor();await screen('signup');
   await page.getByRole('tab',{name:'Sign in'}).click();await page.getByRole('heading',{name:'Welcome back'}).waitFor();
   await page.getByRole('button',{name:'Show password'}).click();
   if(await page.locator('#auth-password').getAttribute('type')!=='text')throw Error('Password visibility toggle failed');
 } else {
   if(!authHeading.includes('Sign in'))throw Error('Unexpected unconfigured sign-in heading: '+authHeading);
   await page.getByText('Accounts aren’t configured on this deployment.',{exact:false}).waitFor();
 }
 await page.goto(base+'/account');await page.getByRole('heading',{name:'No account is signed in.'}).waitFor();await screen('account-signed-out');
 await page.goto(base+'/privacy');await page.getByRole('heading',{name:'Privacy & your data'}).waitFor();
 await page.getByText('No account is required.',{exact:false}).waitFor();
 const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const mp=await mobile.newPage();mp.on('pageerror',e=>errors.push(e.message));
 await mp.goto(base);await mp.getByRole('heading',{name:'Your preparation.'}).waitFor();await mp.screenshot({path:'.cache/screenshots/mobile-overview.png',fullPage:true});
 await mp.getByRole('link',{name:'Assess my readiness',exact:true}).last().click();
 await mp.getByRole('button',{name:'Save & continue'}).waitFor();
 await mp.screenshot({path:'.cache/screenshots/mobile-assessment.png',fullPage:true});
 const overflow=await mp.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(overflow)throw Error('Mobile horizontal overflow');
 await mp.getByRole('button',{name:'Toggle navigation'}).click();await mp.getByRole('link',{name:'My progress',exact:true}).click();await mp.getByRole('heading',{name:'Your starting line is waiting.'}).waitFor();
 // Narrow browser has a separate storage partition/context: no other visitor's history.
 await mp.getByRole('button',{name:'Toggle navigation'}).click();await mp.getByRole('link',{name:'Assess my readiness',exact:true}).first().click();
 for(let i=0;i<5;i++){
   await mp.getByRole('button',{name:i===4?'Review my answers':'Save & continue',exact:true}).click();
   await mp.getByText(i===4?'One last look before your results.':`Section ${i+2} of 5`,{exact:false}).waitFor();
 }
 await mp.getByRole('button',{name:'Calculate my readiness'}).click();await mp.getByRole('heading',{name:'Here’s where you stand.'}).waitFor();
 await mp.screenshot({path:'.cache/screenshots/mobile-results.png',fullPage:true});
 if(await mp.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile results overflow');

 if(errors.length)throw Error(errors.join('\n'));
 console.log('PASS: desktop assessment/validation/repeat/save, plan ticks, CSV download, backup/delete/restore, model inference, mobile layout/navigation, cross-context history isolation; JS errors: 0.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
