"""Loopback-only companion. No audio leaves this computer."""
import os, io, tempfile, subprocess, sys, secrets, getpass
from pathlib import Path
from flask import Flask, request, Response, send_from_directory, jsonify
ROOT=Path(__file__).resolve().parents[1]; app=Flask(__name__); app.config['MAX_CONTENT_LENGTH']=512*1024*1024
PIN=os.environ.get('MIX_PIN') or getpass.getpass('MIX STUDIO PIN (4 digits): ')
if len(PIN)!=4 or not PIN.isascii() or not PIN.isdigit(): raise SystemExit('4 ASCII digits required')
@app.before_request
def guard():
    if request.host != '127.0.0.1:8765': return Response('Invalid host',403)
    a=request.authorization
    if not a or a.username!='studio' or not secrets.compare_digest(a.password or '',PIN): return Response('Login required',401,{'WWW-Authenticate':'Basic realm="MIX STUDIO"'})
    if request.method=='POST' and (request.headers.get('Origin')!='http://127.0.0.1:8765' or request.headers.get('X-Mix-Local')!='1'): return Response('Forbidden',403)
@app.after_request
def headers(r):
    r.headers['Cache-Control']='no-store'; r.headers['X-Content-Type-Options']='nosniff'; return r
@app.get('/')
def home(): return send_from_directory(ROOT,'index.html')
@app.get('/logout')
def logout(): return Response('ブラウザを閉じて認証情報を消去してください。',401,{'WWW-Authenticate':'Basic realm="MIX STUDIO"'})
@app.get('/<path:name>')
def asset(name):
    if name in ('dsp.js','worker.js','mp3.js','extra.js'): return send_from_directory(ROOT,name)
    if name=='vendor/lame.min.js': return send_from_directory(ROOT/'node_modules/lamejs','lame.min.js')
    return Response('Not found',404)
@app.get('/api/status')
def status(): return jsonify(local=True)
def read_audio(file):
    import soundfile as sf
    x,sr=sf.read(file,dtype='float32',always_2d=True); return x,sr
def wave(x,sr):
    import soundfile as sf
    b=io.BytesIO(); sf.write(b,x,sr,format='WAV',subtype='FLOAT'); return Response(b.getvalue(),mimetype='audio/wav')
@app.post('/api/pitch')
def pitch():
    import torch, torchcrepe, numpy as np
    x,sr=read_audio(request.files['audio']); hop=round(sr*.02); device='cuda' if torch.cuda.is_available() else 'cpu'
    with torch.inference_mode():
        f,p=torchcrepe.predict(torch.from_numpy(x.mean(axis=1)).unsqueeze(0),sr,hop,65,1100,model='tiny',batch_size=512,device=device,return_periodicity=True)
    f=f.cpu().numpy().ravel(); p=p.cpu().numpy().ravel(); f=np.where((p>.35)&np.isfinite(f),f,0)
    return jsonify(hop=hop,f0=f.tolist())
@app.post('/api/noise')
def noise():
    import torch, librosa, numpy as np
    from df.enhance import init_df, enhance
    x,sr=read_audio(request.files['audio']); model,state,_=init_df(); rate=state.sr(); y=librosa.resample(x.T,orig_sr=sr,target_sr=rate)
    with torch.inference_mode(): z=enhance(model,state,torch.from_numpy(y.copy()),pad=True).cpu().numpy()
    z=librosa.resample(z,orig_sr=rate,target_sr=sr).T; z=librosa.util.fix_length(z,size=len(x),axis=0)
    amount=float(request.form.get('amount','.5')); amount=max(0,min(1,amount)); return wave(x*(1-amount)+z*amount,sr)
@app.post('/api/separate')
def separate():
    import torch
    stem=request.form.get('stem','vocals'); assert stem in ('vocals','no_vocals')
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp); request.files['audio'].save(p/'song.wav'); subprocess.run([sys.executable,'-m','demucs','-n','htdemucs','--two-stems','vocals','-d','cuda' if torch.cuda.is_available() else 'cpu','-o',tmp,str(p/'song.wav')],check=True)
        return Response((p/'htdemucs/song'/f'{stem}.wav').read_bytes(),mimetype='audio/wav')
@app.post('/api/timing')
def timing():
    import librosa, numpy as np
    x,sr=read_audio(request.files['audio']); ref,rr=read_audio(request.files['reference']); rate=22050; hop=512
    a=librosa.resample(x.mean(axis=1),orig_sr=sr,target_sr=rate); b=librosa.resample(ref.mean(axis=1),orig_sr=rr,target_sr=rate)
    # Chroma DTW aligns sung notes with a guide vocal; not arbitrary accompaniment.
    A=librosa.feature.chroma_stft(y=a,sr=rate,hop_length=hop); B=librosa.feature.chroma_stft(y=b,sr=rate,hop_length=hop)
    if max(A.shape[1],B.shape[1])>16000: raise ValueError('Timing guide too long; split into sections')
    _,path=librosa.sequence.dtw(X=A,Y=B,metric='euclidean',global_constraints=True,band_rad=.15); path=path[::-1]
    # Piecewise phase-vocoder stretch, bounded to avoid extreme timing changes.
    ends=list(range(0,B.shape[1],max(1,round(2*rate/hop))))+[B.shape[1]-1]; ends=sorted(set(ends)); src=[]
    for t in ends: src.append(int(np.median(path[np.abs(path[:,1]-t)==np.min(np.abs(path[:,1]-t)),0])))
    src[0]=0; src[-1]=A.shape[1]-1; parts=[]
    for j in range(len(ends)-1):
        lo=round(src[j]*hop*sr/rate); hi=min(len(x),round(src[j+1]*hop*sr/rate)); n=max(1,round((ends[j+1]-ends[j])*hop*sr/rate)); seg=x[lo:hi].T
        if seg.shape[-1]<2048 or not .65<=seg.shape[-1]/n<=1.55: raise ValueError('Guide differs too much; use a matching vocal guide or shorter section')
        z=librosa.effects.time_stretch(seg,rate=seg.shape[-1]/n).T; parts.append(librosa.util.fix_length(z,size=n,axis=0))
    return wave(np.concatenate(parts,axis=0),sr)
@app.errorhandler(Exception)
def fail(e):
    app.logger.exception('Processing failed'); return jsonify(error=str(e)),getattr(e,'code',500)
if __name__=='__main__': app.run(host='127.0.0.1',port=8765,debug=False,threaded=False)
