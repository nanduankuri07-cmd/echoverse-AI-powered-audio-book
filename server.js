// server.js
import express from "express";
import cors from "cors";
import multer from "multer";
import fs from "fs";
import path from "path";
import dotenv from "dotenv";
dotenv.config();

import { IamAuthenticator } from "ibm-cloud-sdk-core";
import TextToSpeechV1 from "ibm-watson/text-to-speech/v1.js";
import SpeechToTextV1 from "ibm-watson/speech-to-text/v1.js";

// watsonx (Granite)
import { WatsonX } from "@ibm-cloud/watsonx-ai"; // npm i @ibm-cloud/watsonx-ai

const app = express();
app.use(cors());
app.use(express.json({ limit: "2mb" }));
app.use(express.urlencoded({ extended: true, limit: "2mb" }));
app.use(express.static("public"));

const PORT = process.env.PORT || 3000;

/* ---------- watsonx: Granite LLM ---------- */
const wx = new WatsonX({
  version: "2024-05-31", // SDK version string
  serviceUrl: process.env.WATSONX_URL,
  authenticator: {
    authenticate: async (options) => {
      options.headers = options.headers || {};
      options.headers["Authorization"] = `Bearer ${process.env.WATSONX_API_KEY}`;
      return Promise.resolve();
    }
  },
});

// Helper: select Granite model (text-generation)
const GRANITE_MODEL = "ibm/granite-13b-instruct-v2"; // change to any hosted Granite you enabled

app.post("/api/generate", async (req, res) => {
  try {
    const { prompt, task = "rewrite", tone = "Neutral" } = req.body;

    const system = `You are EchoVerse's writer. Task: ${task}.
Tone: ${tone}. Keep meaning intact. Output only the transformed text.`;

    const generateParams = {
      modelId: GRANITE_MODEL,
      input: prompt,
      projectId: process.env.WATSONX_PROJECT_ID,
      parameters: {
        decoding_method: "greedy",
        max_new_tokens: 400,
        stop_sequences: [],
        temperature: 0.2,
      },
      // optional system prompt
      context: { system_prompt: system },
    };

    const result = await wx.generateText(generateParams);
    // SDK shapes can vary; normalize possible fields:
    const text =
      result?.result?.generated_text ??
      result?.generated_text ??
      result?.result?.output_text ??
      JSON.stringify(result);

    res.json({ text });
  } catch (err) {
    console.error("watsonx error:", err?.response?.result || err);
    res.status(500).json({ error: "Granite generation failed" });
  }
});

/* ---------- IBM Watson: Text-to-Speech ---------- */
const tts = new TextToSpeechV1({
  authenticator: new IamAuthenticator({ apikey: process.env.TTS_API_KEY }),
  serviceUrl: process.env.TTS_URL,
});

app.post("/api/tts", async (req, res) => {
  try {
    const { text, voice = process.env.TTS_VOICE || "en-US_AllisonV3Voice", format = "audio/mp3" } = req.body;

    const synth = await tts.synthesize({
      text,
      accept: format, // "audio/mp3" | "audio/wav" | "audio/ogg;codecs=opus"
      voice,
    });
    const audio = await tts.repairWavHeaderStream(synth.result); // harmless for mp3 too
    res.setHeader("Content-Type", format);
    res.send(audio);
  } catch (err) {
    console.error("TTS error:", err?.response?.result || err);
    res.status(500).json({ error: "TTS failed" });
  }
});

/* ---------- IBM Watson: Speech-to-Text ---------- */
const stt = new SpeechToTextV1({
  authenticator: new IamAuthenticator({ apikey: process.env.STT_API_KEY }),
  serviceUrl: process.env.STT_URL,
});

const upload = multer({ dest: "uploads/" });

app.post("/api/stt", upload.single("audio"), async (req, res) => {
  try {
    const audioPath = req.file.path;
    const contentType = req.file.mimetype || "audio/webm";
    const audioStream = fs.createReadStream(audioPath);

    const sttResp = await stt.recognize({
      audio: audioStream,
      contentType, // e.g. "audio/webm;codecs=opus" or "audio/wav"
      model: "en-US_BroadbandModel",
      // wordAlternativesThreshold: 0.9,
      // smartFormatting: true,
    });

    fs.unlink(audioPath, () => {});

    const transcript =
      sttResp?.result?.results?.map(r => r.alternatives?.[0]?.transcript || "").join(" ").trim() || "";

    res.json({ transcript });
  } catch (err) {
    console.error("STT error:", err?.response?.result || err);
    res.status(500).json({ error: "STT failed" });
  }
});

app.listen(PORT, () => console.log(`✅ Server listening on http://localhost:${PORT}`));
