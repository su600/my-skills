#!/usr/bin/env node
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const MODEL = 'openai/gpt-image-2.5-flare';
const API_URL = 'https://openrouter.ai/api/v1/images';
const validRatios = new Set([
  '1:1', '1:2', '1:4', '1:8', '2:1', '2:3', '2.35:1', '3:2', '3:4',
  '4:1', '4:3', '4:5', '5:2', '5:4', '5:7', '7:5', '8:1', '9:16',
  '16:9', '9:19.5', '19.5:9', '9:20', '20:9', '9:21', '21:9', 'auto',
]);

function argValue(name, fallback) {
  const i = process.argv.indexOf(name);
  return i === -1 ? fallback : process.argv[i + 1];
}

const aspectRatio = argValue('--aspect-ratio', 'auto');
const defaultOutputDir = path.join(process.env.HOME ?? process.cwd(), 'Pictures', 'GeneratedImages');
const outputDir = path.resolve(argValue('--output-dir', defaultOutputDir));
if (!validRatios.has(aspectRatio)) {
  console.error(`Unsupported aspect ratio: ${aspectRatio}`);
  process.exit(2);
}

// Configure an authorized key source privately; never commit credentials.
let apiKey = process.env.OPENROUTER_API_KEY;
let credentialSource = apiKey ? 'environment' : '';
if (!apiKey) {
  const authPath = path.join(process.env.HOME ?? '', '.pi', 'agent', 'auth.json');
  try {
    const auth = JSON.parse(await readFile(authPath, 'utf8'));
    const storedKey = auth?.openrouter?.key;
    if (typeof storedKey === 'string' && storedKey.trim()) {
      apiKey = storedKey.trim();
      credentialSource = 'Pi auth.json';
    }
  } catch (error) {
    if (error?.code !== 'ENOENT') {
      console.error('Could not read the Pi authentication configuration.');
      process.exit(2);
    }
  }
}
if (!apiKey) {
  console.error('No OpenRouter credential is configured in OPENROUTER_API_KEY or Pi auth.json.');
  process.exit(2);
}
if (process.argv.includes('--check-auth')) {
  console.log(`OpenRouter credential available from ${credentialSource}; value was not displayed.`);
  process.exit(0);
}

let prompt = '';
for await (const chunk of process.stdin) prompt += chunk;
prompt = prompt.trim();
if (!prompt) {
  console.error('Pass the approved image prompt through stdin.');
  process.exit(2);
}

const response = await fetch(API_URL, {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${apiKey}`,
    'Content-Type': 'application/json',
    'HTTP-Referer': 'https://openrouter.ai/',
    'X-Title': 'Pi OpenRouter Image Generator',
  },
  body: JSON.stringify({
    model: MODEL,
    prompt,
    aspect_ratio: aspectRatio,
    output_format: 'png',
    n: 1,
  }),
});

if (!response.ok) {
  console.error(`OpenRouter image request failed (${response.status} ${response.statusText}).`);
  process.exit(1);
}

const result = await response.json();
const image = result.data?.[0];
if (!image) {
  console.error('OpenRouter response did not contain data[0].');
  process.exit(1);
}

let bytes;
if (image.b64_json) {
  bytes = Buffer.from(image.b64_json, 'base64');
} else if (image.url) {
  const imageResponse = await fetch(image.url);
  if (!imageResponse.ok) {
    console.error(`Could not download generated image (${imageResponse.status}).`);
    process.exit(1);
  }
  bytes = Buffer.from(await imageResponse.arrayBuffer());
} else {
  console.error('OpenRouter response contained neither b64_json nor url.');
  process.exit(1);
}

const contentType = image.mime_type ?? image.media_type ?? '';
const extension = contentType.includes('jpeg') ? 'jpg' : contentType.includes('webp') ? 'webp' : 'png';
await mkdir(outputDir, { recursive: true });
const filename = `image-${new Date().toISOString().replaceAll(':', '-').replaceAll('.', '-')}.${extension}`;
const outputPath = path.join(outputDir, filename);
await writeFile(outputPath, bytes, { flag: 'wx' });
console.log(JSON.stringify({ path: outputPath, model: MODEL, aspect_ratio: aspectRatio, bytes: bytes.length }));
