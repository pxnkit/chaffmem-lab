import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the ChaffMem research interface", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>ChaffMem Lab \| Memory Availability Research<\/title>/i);
  assert.match(html, /Measure when agent memory/);
  assert.match(html, /Experiment builder/);
  assert.match(html, /Memory map/);
  assert.match(html, /Trace inspector/);
  assert.match(html, /A working instrument, not a finished claim/);
  assert.match(html, /No commercial system is evaluated or named/);
  assert.match(html, /role="tablist"/);
  assert.match(html, /aria-selected="true"/);
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/);
});

test("ships the product simulator and removes starter-only assets", async () => {
  const [simulator, page, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/simulator.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(simulator, /runSimulation/);
  assert.match(simulator, /semantic_nearest/);
  assert.match(simulator, /canary_adaptive/);
  assert.match(simulator, /stableTraceHash/);
  assert.match(page, /<Explorer \/>/);
  assert.match(layout, /generateMetadata/);
  assert.match(layout, /\/og\.png/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  await assert.rejects(access(new URL("../app/_sites-preview", projectRoot)));
});
