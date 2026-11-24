const encoder = new TextEncoder();
async function sign(secret, message) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), {name:'HMAC',hash:'SHA-256'}, false, ['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,encoder.encode(message))), x=>x.toString(16).padStart(2,'0')).join('');
}
function equal(a,b){if(a.length!==b.length)return false;let n=0;for(let i=0;i<a.length;i++)n|=a.charCodeAt(i)^b.charCodeAt(i);return n===0;}
const headers={'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow','X-Content-Type-Options':'nosniff'};
function login(error='',status=200){return new Response(`<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>MIX STUDIO / LOGIN</title><style>body{background:#121117;color:#eee;font:16px system-ui;display:grid;place-items:center;min-height:95vh}form{width:min(340px,85vw);padding:30px;border:1px solid #413444;border-radius:16px;background:#201e28}h1{color:#ff92c2}input,button{box-sizing:border-box;width:100%;padding:13px;margin:10px 0;border-radius:8px;border:1px solid #554657;font:inherit}input{background:#14131a;color:#fff}button{background:#e982b4;color:#211520;font-weight:bold}small{color:#aaa}</style><form method="post" action="/login"><h1>MIX STUDIO</h1><small>PRIVATE ACCESS</small><p>${error}</p><label>アクセスパスワード<input type="password" name="password" inputmode="numeric" pattern="[0-9]{4}" maxlength="4" required autocomplete="current-password"></label><label><input style="width:auto" type="checkbox" name="remember"> ログイン状態を保持する</label><button>ログイン</button></form></html>`,{status,headers:{...headers,'Content-Type':'text/html; charset=utf-8'}})}
export async function onRequest({request,env,next}){
 const url=new URL(request.url);if(!/^\d{4}$/.test(env.ACCESS_PASSWORD||'')||!env.AUTH_DB||!env.SESSION_SECRET||env.SESSION_SECRET.length<32)return new Response('認証設定が必要です。',{status:503,headers});
 const cookie='mix_session';const attrs='; Path=/; HttpOnly; Secure; SameSite=Strict';
 if(url.pathname==='/logout')return new Response(null,{status:303,headers:{...headers,Location:'/','Set-Cookie':cookie+'='+attrs+'; Max-Age=0'}});
 if(url.pathname==='/login'&&request.method==='POST'){
  if(request.headers.get('Origin')!==url.origin)return new Response('Forbidden',{status:403,headers});
  let f;try{f=await request.formData()}catch{return login('入力を確認してください。',400)}
  // Global limit protects the four-digit PIN even across changing IP addresses.
  const windowId=Math.floor(Date.now()/900000);
  let attempt;
  try {
   attempt=await env.AUTH_DB.prepare('INSERT INTO auth_attempts (id, window_id, attempts) VALUES (1, ?, 1) ON CONFLICT(id) DO UPDATE SET attempts=CASE WHEN window_id=excluded.window_id THEN MIN(attempts+1,6) ELSE 1 END, window_id=excluded.window_id RETURNING attempts').bind(windowId).first();
  } catch {return new Response('認証サービスを利用できません。',{status:503,headers});}
  if(!attempt||attempt.attempts>5)return login('試行回数の上限に達しました。15分以内に解除されます。',429);
  const supplied=String(f.get('password')||'');if(!/^\d{4}$/.test(supplied)||!equal(await sign(env.SESSION_SECRET,supplied),await sign(env.SESSION_SECRET,env.ACCESS_PASSWORD)))return login('パスワードが違います。',401);
  const age=f.get('remember')?604800:28800;const exp=String(Math.floor(Date.now()/1000)+age);const sig=await sign(env.SESSION_SECRET,exp+':'+env.ACCESS_PASSWORD);return new Response(null,{status:303,headers:{...headers,Location:'/','Set-Cookie':cookie+'='+exp+'.'+sig+attrs+(f.get('remember')?'; Max-Age='+age:'')}});
 }
 const token=(request.headers.get('Cookie')||'').match(/(?:^|;\s*)mix_session=([^;]+)/)?.[1]||'';const [exp,sig]=token.split('.');if(!exp||!sig||!/^\d+$/.test(exp)||Number(exp)<=Date.now()/1000||!equal(sig,await sign(env.SESSION_SECRET,exp+':'+env.ACCESS_PASSWORD)))return login();
 const response=await next();let h=new Headers(response.headers);for(const [k,v] of Object.entries(headers))h.set(k,v);return new Response(response.body,{status:response.status,statusText:response.statusText,headers:h});
}
