

const express = require('express');
const fileUpload = require('express-fileupload');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
require('dotenv').config();

// IBM SDKs
const { IamAuthenticator } = require('ibm-watson/auth');
const TextToSpeechV1 = require('ibm-watson/text-to-speech/v1');
const LanguageTranslatorV3 = require('ibm-watson/language-translator/v3');

const app = express();
app.use(cors());
app.use(express.json({ limit: '2mb' }));
app.use(fileUpload());

// ---------- IBM Text to Speech ----------
const tts = new TextToSpeechV1({
  authenticator: new IamAuthenticator({ apikey: process.env.TTS_API_KEY }),
  serviceUrl: process.env.TTS_URL,
});

app.post('/api/tts', async (req, res) => {
  try {
    const { text, voice = 'en-US_AllisonV3Voice', accept = 'audio/mp3' } = req.body || {};
    if (!text || !text.trim()) return res.status(400).json({ error: 'Missing text' });

    const { result } = await tts.synthesize({ text, voice, accept });
    const repaired = await tts.repairWavHeaderStream(result);

    res.set({
      'Content-Type': accept,
      'Content-Disposition': 'inline; filename="speech.mp3"',
      'Cache-Control': 'no-store',
    });
    res.send(repaired);
  } catch (err) {
    console.error('TTS error', err);
    res.status(500).json({ error: 'TTS failed', details: err?.message });
  }
});

// ---------- IBM Language Translator ----------
const translator = new LanguageTranslatorV3({
  version: '2023-10-24',
  authenticator: new IamAuthenticator({ apikey: process.env.LT_API_KEY }),
  serviceUrl: process.env.LT_URL,
});

app.post('/api/translate', async (req, res) => {
  try {
    const { text, source, target } = req.body || {};
    if (!text || !source || !target) {
      return res.status(400).json({ error: 'Provide text, source, target (e.g., en→te, hi→en, te→en)' });
    }
    const { result } = await translator.translate({
      text: [text],
      source,
      target,
    });
    const translation = result?.translations?.[0]?.translation || '';
    res.json({ translation });
  } catch (err) {
    console.error('Translate error', err);
    res.status(500).json({ error: 'Translation failed', details: err?.message });
  }
});

// ---------- Q&A (Stub) ----------
// Choose ONE of the following in production:
// 1) Watson Assistant v2 (dialog skill)
// 2) watsonx.ai text-generation (e.g., Granite models) with grounding
// For brevity, we echo a helpful message and return a TODO.
app.post('/api/qa', async (req, res) => {
  const { question, context } = req.body || {};
  if (!question) return res.status(400).json({ error: 'Missing question' });
  // TODO: Replace with watsonx.ai or Watson Assistant integration.
  const canned = `Q: ${question}\n\n(Context-aware answers go here. Hook this endpoint to watsonx.ai or Watson Assistant.)`;
  res.json({ answer: canned });
});

// ---------- Static hosting (optional) ----------
app.use(express.static(path.join(__dirname, 'public')));

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(`API running on http://localhost:${PORT}`));

/*
.env (create alongside server.js)
---------------------------------
TTS_API_KEY=YOUR_IBM_TTS_API_KEY
TTS_URL=YOUR_IBM_TTS_URL              # e.g. https://api.us-south.text-to-speech.watson.cloud.ibm.com
LT_API_KEY=YOUR_IBM_LT_API_KEY
LT_URL=YOUR_IBM_LT_URL                # e.g. https://api.us-south.language-translator.watson.cloud.ibm.com
# Optional for Q&A if you wire it up later:
WATSONX_API_KEY=...
WATSONX_URL=...
ASSISTANT_API_KEY=...
ASSISTANT_URL=...
ASSISTANT_ID=...
*/

// =============================
// File: App.jsx  (React UI)
// =============================
import React, { useMemo, useRef, useState } from 'react';

export default function App() {
  const [tab, setTab] = useState('qa');

  return (
    <div className="min-h-screen bg-black text-white">
      <header className="px-6 py-5 border-b border-white/10 sticky top-0 backdrop-blur">
        <h1 className="text-2xl font-bold">Watson-Powered Studio</h1>
        <p className="text-sm text-white/70">Q&A • Translation (EN ↔ HI ↔ TE) • High-Quality Voice Narration</p>
        <nav className="mt-4 flex gap-2">
          {['qa','translate','tts'].map(id => (
            <button key={id}
              onClick={() => setTab(id)}
              className={`px-4 py-2 rounded-2xl border ${tab===id? 'bg-white text-black':'border-white/20 hover:bg-white/10'}`}
            >{id === 'qa' ? 'Q&A' : id === 'translate' ? 'Translate' : 'Narrate'}</button>
          ))}
        </nav>
      </header>

      <main className="p-6 grid gap-6 max-w-5xl mx-auto">
        {tab === 'qa' && <QnA />}
        {tab === 'translate' && <Translate />}
        {tab === 'tts' && <Narrate />}
      </main>

      <footer className="p-6 text-center text-white/50">Built with IBM Watson Text-to-Speech & Language Translator. Q&A endpoint is pluggable.</footer>
    </div>
  );
}

function QnA(){
  const [question, setQuestion] = useState('What is this app capable of?');
  const [context, setContext] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    setLoading(true); setAnswer('');
    try{
      const res = await fetch('/api/qa', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ question, context })});
      const data = await res.json();
      setAnswer(data.answer || JSON.stringify(data));
    }catch(err){ setAnswer('Error: '+err.message); }
    finally{ setLoading(false); }
  };

  return (
    <section className="grid gap-3">
      <label className="text-sm text-white/70">Question</label>
      <textarea value={question} onChange={e=>setQuestion(e.target.value)} className="w-full min-h-[90px] p-3 rounded-2xl bg-white/5 border border-white/10 outline-none" placeholder="Ask anything..." />

      <label className="text-sm text-white/70">(Optional) Context / Reference</label>
      <textarea value={context} onChange={e=>setContext(e.target.value)} className="w-full min-h-[90px] p-3 rounded-2xl bg-white/5 border border-white/10 outline-none" placeholder="Paste notes, a paragraph, or facts to ground the answer." />

      <div className="flex gap-2">
        <button onClick={ask} disabled={loading} className="px-4 py-2 rounded-2xl bg-white text-black disabled:opacity-50">{loading?'Thinking…':'Ask'}</button>
        <button onClick={()=>{setQuestion(''); setContext(''); setAnswer('');}} className="px-4 py-2 rounded-2xl border border-white/20">Clear</button>
      </div>

      <div className="mt-3 p-4 rounded-2xl bg-white/5 border border-white/10 whitespace-pre-wrap min-h-[80px]">{answer || 'The answer will appear here.'}</div>
    </section>
  );
}

function Translate(){
  const [text, setText] = useState('Hello! How are you?');
  const [mode, setMode] = useState('en-te');
  const [out, setOut] = useState('');
  const [loading, setLoading] = useState(false);

  const options = [
    { id:'en-te', label:'English → Telugu', source:'en', target:'te' },
    { id:'hi-en', label:'Hindi → English', source:'hi', target:'en' },
    { id:'te-en', label:'Telugu → English', source:'te', target:'en' },
  ];

  const choice = useMemo(()=> options.find(o=>o.id===mode), [mode]);

  const run = async () => {
    setLoading(true); setOut('');
    try{
      const res = await fetch('/api/translate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ text, source: choice.source, target: choice.target }) });
      const data = await res.json();
      setOut(data.translation || JSON.stringify(data));
    }catch(err){ setOut('Error: '+err.message); }
    finally{ setLoading(false); }
  };

  return (
    <section className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        {options.map(o=> (
          <button key={o.id} className={`px-3 py-2 rounded-2xl border ${mode===o.id? 'bg-white text-black':'border-white/20 hover:bg-white/10'}`} onClick={()=>setMode(o.id)}>{o.label}</button>
        ))}
      </div>

      <textarea value={text} onChange={e=>setText(e.target.value)} className="w-full min-h-[120px] p-3 rounded-2xl bg-white/5 border border-white/10 outline-none" placeholder="Type or paste text to translate" />
      <div className="flex gap-2">
        <button onClick={run} disabled={loading} className="px-4 py-2 rounded-2xl bg-white text-black disabled:opacity-50">{loading?'Translating…':'Translate'}</button>
        <button onClick={()=>{setText(''); setOut('');}} className="px-4 py-2 rounded-2xl border border-white/20">Clear</button>
      </div>
      <div className="mt-3 p-4 rounded-2xl bg-white/5 border border-white/10 whitespace-pre-wrap min-h-[80px]">{out || 'Translation will appear here.'}</div>
    </section>
  );
}

function Narrate(){
  const [text, setText] = useState('Welcome to the Watson-powered narrator!');
  const [voice, setVoice] = useState('en-US_AllisonV3Voice');
  const [loading, setLoading] = useState(false);
  const audioRef = useRef(null);

  const speak = async () => {
    setLoading(true);
    try{
      const res = await fetch('/api/tts', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ text, voice, accept:'audio/mp3' })});
      if(!res.ok) throw new Error('TTS failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = audioRef.current;
      a.src = url; a.play();

      // Create a download link dynamically
      const dl = document.getElementById('tts-download');
      dl.href = url; dl.download = 'narration.mp3';
      dl.classList.remove('pointer-events-none','opacity-40');
    }catch(err){ alert(err.message); }
    finally{ setLoading(false); }
  };

  return (
    <section className="grid gap-3">
      <textarea value={text} onChange={e=>setText(e.target.value)} className="w-full min-h-[130px] p-3 rounded-2xl bg-white/5 border border-white/10 outline-none" placeholder="Enter text to narrate" />

      <div className="flex flex-wrap items-center gap-3">
        <label className="text-sm text-white/70">Voice</label>
        <select value={voice} onChange={e=>setVoice(e.target.value)} className="px-3 py-2 rounded-2xl bg-white/5 border border-white/10">
          <option value="en-US_AllisonV3Voice">Allison (en-US)</option>
          <option value="en-US_LisaV3Voice">Lisa (en-US)</option>
          <option value="en-US_MichaelV3Voice">Michael (en-US)</option>
          {/* Add more supported voices as needed */}
        </select>

        <button onClick={speak} disabled={loading || !text.trim()} className="px-4 py-2 rounded-2xl bg-white text-black disabled:opacity-50">{loading?'Generating…':'Speak'}</button>
        <a id="tts-download" className="px-4 py-2 rounded-2xl border border-white/20 pointer-events-none opacity-40" href="#">Download MP3</a>
      </div>

      <audio ref={audioRef} controls className="mt-2 w-full" />
      <p className="text-xs text-white/60">Tip: Generate first, then use the Download MP3 button.</p>
    </section>
  );
}

// =============================
// Quick Start (README)
// =============================
// 1) Save this file as App.jsx and the backend as server.js
// 2) Backend setup:
//    npm init -y
//    npm i express cors express-fileupload dotenv ibm-watson
//    # create .env (see keys above)
//    node server.js  # runs on http://localhost:3001
// 3) Frontend setup (one quick option using Vite):
//    npm create vite@latest watson-studio -- --template react
//    cd watson-studio && npm i && npm i -D tailwindcss postcss autoprefixer
//    npx tailwindcss init -p
//    // Configure Tailwind (content: ['./index.html','./src/**/*.{js,jsx,ts,tsx}'])
//    // Replace src/App.jsx with this App.jsx content, and ensure the dev server proxies to 3001.
//    // vite.config.js -> server: { proxy: { '/api': 'http://localhost:3001' } }
//    npm run dev
// 4) Production: host server.js behind HTTPS; never expose IBM keys to the browser.
