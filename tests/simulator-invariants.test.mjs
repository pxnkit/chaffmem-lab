import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

const source = await readFile(
  new URL("../app/simulator.ts", import.meta.url),
  "utf8",
);
const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
  fileName: "simulator.ts",
});
const simulator = await import(
  `data:text/javascript;base64,${Buffer.from(transpiled.outputText).toString("base64")}`
);

test("simulation is deterministic and zero-budget metrics include baseline", () => {
  const config = { ...simulator.defaultConfig, budget: 0 };
  const first = simulator.runSimulation(config);
  const second = simulator.runSimulation(config);
  assert.deepEqual(first, second);
  assert.equal(first.trajectory.length, 1);
  assert.equal(first.metrics.criticalRecall, first.trajectory[0].recall);
  assert.equal(first.metrics.physicalAvailability, 1);
});

test("retrieval budget and knowledge condition affect bounded outcomes", () => {
  const base = {
    ...simulator.defaultConfig,
    capacity: 80,
    budget: 60,
    defense: "none",
    attack: "semantic_nearest",
    knowledge: "query",
  };
  const narrow = simulator.runSimulation({ ...base, topK: 1 });
  const wide = simulator.runSimulation({ ...base, topK: 12 });
  assert.ok(wide.metrics.criticalRecall >= narrow.metrics.criticalRecall);

  const zero = simulator.runSimulation({ ...base, knowledge: "zero" });
  const informed = simulator.runSimulation(base);
  const zeroTraffic = zero.points.find((point) => point.id === "chaff-001");
  const informedTraffic = informed.points.find((point) => point.id === "chaff-001");
  assert.ok(zeroTraffic);
  assert.ok(informedTraffic);
  assert.notDeepEqual(
    [zeroTraffic.x, zeroTraffic.y],
    [informedTraffic.x, informedTraffic.y],
  );
});

test("step snapshots and reservoir sampling stay bounded", () => {
  const result = simulator.runSimulation({
    ...simulator.defaultConfig,
    policy: "reservoir",
    defense: "none",
    capacity: 8,
    budget: 40,
  });
  assert.equal(result.states.length, 41);
  assert.equal(result.states[0].step, 0);
  assert.ok(result.states.every((state) => state.retainedIds.length <= 8));
  assert.ok(result.trajectory.every((point) => point.alertScore >= 0));
  assert.ok(result.trajectory.every((point) => point.alertScore <= 1));
});

test("matched defenses preserve coordinates for shared traffic records", () => {
  const config = {
    ...simulator.defaultConfig,
    attack: "sybil",
    budget: 30,
    defense: "none",
  };
  const undefended = simulator.runSimulation(config);
  const defended = simulator.runSimulation({
    ...config,
    defense: "origin_quota",
  });
  const defendedById = new Map(defended.points.map((point) => [point.id, point]));
  const shared = undefended.points.filter((point) => defendedById.has(point.id));
  assert.ok(shared.length > 0);
  for (const point of shared) {
    const matched = defendedById.get(point.id);
    assert.deepEqual([point.x, point.y], [matched.x, matched.y]);
  }
});

test("result digest covers outcome-changing configuration", () => {
  const first = simulator.runSimulation({
    ...simulator.defaultConfig,
    topK: 2,
  });
  const second = simulator.runSimulation({
    ...simulator.defaultConfig,
    topK: 8,
  });
  assert.notEqual(first.digest, second.digest);
  assert.match(first.digest, /^[a-f0-9]{32}$/);
});
