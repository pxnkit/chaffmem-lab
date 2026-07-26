export type MemoryPolicy =
  | "fifo"
  | "lru"
  | "reservoir"
  | "importance"
  | "mmr"
  | "hybrid";

export type AttackStrategy =
  | "none"
  | "random"
  | "same_domain"
  | "semantic_nearest"
  | "diverse"
  | "sybil"
  | "adaptive";

export type DefenseStrategy =
  | "none"
  | "duplicate_control"
  | "origin_quota"
  | "semantic_coverage"
  | "criticality_retention"
  | "canary_adaptive";

export type KnowledgeLevel =
  | "zero"
  | "query"
  | "concept"
  | "black_box"
  | "white_box";

export type Domain = "travel" | "healthcare" | "operations" | "finance";

export interface ExperimentConfig {
  policy: MemoryPolicy;
  attack: AttackStrategy;
  defense: DefenseStrategy;
  knowledge: KnowledgeLevel;
  domain: Domain;
  capacity: number;
  topK: number;
  budget: number;
  seed: number;
}

export interface MemoryPoint {
  id: string;
  content: string;
  kind: "critical" | "background" | "chaff";
  origin: string;
  x: number;
  y: number;
  importance: number;
  createdAt: number;
  lastAccess: number;
  cell: string;
  retained: boolean;
  currentRank: number | null;
}

export interface RetrievalQuery {
  text: string;
  x: number;
  y: number;
}

export interface MemoryStepState {
  step: number;
  retainedIds: string[];
  ranks: Record<string, number>;
}

export interface TrajectoryPoint {
  step: number;
  recall: number;
  physical: number;
  rank: number | null;
  downstreamAvailable: number;
  occupancy: number;
  alertScore: number;
  rejectedWrites: number;
  attackerCost: number;
}

export interface TraceDecision {
  id: string;
  step: number;
  kind: "seed" | "write" | "defense" | "eviction" | "retrieval";
  title: string;
  reason: string;
  recordId: string | null;
  candidateCount: number;
  targetRank: number | null;
  hash: string;
  previousHash: string;
}

export interface RunMetrics {
  criticalRecall: number;
  physicalAvailability: number;
  downstreamAvailability: number;
  finalTargetRank: number | null;
  writesToFailure: number | null;
  acceptedWrites: number;
  rejectedWrites: number;
  peakAlertScore: number;
}

export interface RunResult {
  runId: string;
  createdAt: string;
  config: ExperimentConfig;
  query: RetrievalQuery;
  points: MemoryPoint[];
  states: MemoryStepState[];
  trajectory: TrajectoryPoint[];
  trace: TraceDecision[];
  metrics: RunMetrics;
  digest: string;
}

export interface ComparisonArm {
  id: "undefended" | "selected" | "unlimited" | "pinned";
  label: string;
  description: string;
  metrics: RunMetrics;
  trajectory: TrajectoryPoint[];
}

export const defaultConfig: ExperimentConfig = {
  policy: "lru",
  attack: "semantic_nearest",
  defense: "canary_adaptive",
  knowledge: "concept",
  domain: "travel",
  capacity: 24,
  topK: 5,
  budget: 36,
  seed: 17,
};

export const policyLabels: Record<MemoryPolicy, string> = {
  fifo: "FIFO",
  lru: "Least recently used",
  reservoir: "Reservoir sampling",
  importance: "Importance retention",
  mmr: "Diversity retention",
  hybrid: "Metadata and diversity score",
};

export const attackLabels: Record<AttackStrategy, string> = {
  none: "Matched benign traffic",
  random: "Random benign flooding",
  same_domain: "Same-domain flooding",
  semantic_nearest: "Query-nearest chaff",
  diverse: "Diversity-constrained chaff",
  sybil: "Multi-origin flooding",
  adaptive: "Adaptive probe-schedule chaff",
};

export const defenseLabels: Record<DefenseStrategy, string> = {
  none: "No defense",
  duplicate_control: "Near-duplicate control",
  origin_quota: "Per-origin quota",
  semantic_coverage: "Semantic-cell coverage",
  criticality_retention: "Declared high-importance retention",
  canary_adaptive: "Crowding-score adaptive admission",
};

export const knowledgeLabels: Record<KnowledgeLevel, string> = {
  zero: "Zero knowledge",
  query: "Query knowledge",
  concept: "Target concept knowledge",
  black_box: "Distance-query black box",
  white_box: "Distance function white box",
};

export const domainLabels: Record<Domain, string> = {
  travel: "Travel operations",
  healthcare: "Clinic scheduling",
  operations: "Incident response",
  finance: "Expense controls",
};

const targetByDomain: Record<Domain, string> = {
  travel: "The traveler has a severe shellfish allergy and needs verified meal handling",
  healthcare: "The patient requires a latex-free room before the scheduled procedure",
  operations: "Production rollback requires two-person approval before execution",
  finance: "International reimbursements above the limit require compliance review",
};

const queryByDomain: Record<Domain, RetrievalQuery> = {
  travel: {
    text: "What verified food-safety constraint applies to this traveler?",
    x: 39,
    y: 47,
  },
  healthcare: {
    text: "What room preparation constraint applies before the procedure?",
    x: 29,
    y: 48,
  },
  operations: {
    text: "What approval constraint applies before a production rollback?",
    x: 40,
    y: 38,
  },
  finance: {
    text: "What review constraint applies to a large international reimbursement?",
    x: 30,
    y: 37,
  },
};

const benignFragments: Record<Domain, string[]> = {
  travel: [
    "The cafe can prepare vegetarian meals with advance notice",
    "The evening train has quiet-car seating",
    "The hotel stores luggage after checkout",
    "The museum offers timed-entry tickets",
    "The ferry terminal has step-free access",
    "The restaurant accepts reservations for groups",
    "The shuttle leaves every twenty minutes",
    "The market labels common food ingredients",
  ],
  healthcare: [
    "The clinic offers morning appointments",
    "The waiting room has a quiet area",
    "The pharmacy can prepare pre-sorted doses",
    "The lab posts routine results to the portal",
    "The practice sends appointment reminders",
    "The imaging center has accessible changing rooms",
    "The reception desk validates referral details",
    "The care team records dietary preferences",
  ],
  operations: [
    "The service publishes a weekly maintenance window",
    "The on-call handoff includes current alerts",
    "The status page groups incidents by region",
    "The deployment dashboard records release owners",
    "The queue worker emits routine health metrics",
    "The runbook lists standard escalation contacts",
    "The test environment refreshes every morning",
    "The audit log stores completed change reviews",
  ],
  finance: [
    "The expense portal accepts itemized receipts",
    "The finance desk reviews submissions each morning",
    "The card provider posts settled transactions daily",
    "The travel policy lists standard hotel limits",
    "The invoice queue groups entries by department",
    "The reimbursement form supports multiple currencies",
    "The budget report highlights incomplete cost centers",
    "The accounting team closes books each month",
  ],
};

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));
const declaredImportanceThreshold = 0.76;

function mulberry32(seed: number) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function hash(input: string) {
  let h1 = 1779033703;
  let h2 = 3144134277;
  let h3 = 1013904242;
  let h4 = 2773480762;
  for (let index = 0; index < input.length; index += 1) {
    const value = input.charCodeAt(index);
    h1 = h2 ^ Math.imul(h1 ^ value, 597399067);
    h2 = h3 ^ Math.imul(h2 ^ value, 2869860233);
    h3 = h4 ^ Math.imul(h3 ^ value, 951274213);
    h4 = h1 ^ Math.imul(h4 ^ value, 2716044179);
  }
  h1 = Math.imul(h3 ^ (h1 >>> 18), 597399067);
  h2 = Math.imul(h4 ^ (h2 >>> 22), 2869860233);
  h3 = Math.imul(h1 ^ (h3 >>> 17), 951274213);
  h4 = Math.imul(h2 ^ (h4 >>> 19), 2716044179);
  return [h1, h2, h3, h4]
    .map((value) => (value >>> 0).toString(16).padStart(8, "0"))
    .join("");
}

function purposeRandom(seed: number, purpose: string) {
  return mulberry32(
    Number.parseInt(hash(`${seed}|${purpose}`).slice(0, 8), 16),
  );
}

function distance(a: Pick<MemoryPoint, "x" | "y">, b: Pick<MemoryPoint, "x" | "y">) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function semanticCell(x: number, y: number) {
  return `${Math.floor(x / 16)}:${Math.floor(y / 16)}`;
}

function makePoint(
  partial: Omit<MemoryPoint, "cell" | "retained" | "currentRank">,
): MemoryPoint {
  return {
    ...partial,
    cell: semanticCell(partial.x, partial.y),
    retained: true,
    currentRank: null,
  };
}

function stableTraceHash(
  previousHash: string,
  event: Omit<TraceDecision, "id" | "hash" | "previousHash">,
) {
  return hash(
    [
      previousHash,
      event.step,
      event.kind,
      event.title,
      event.reason,
      event.recordId ?? "",
      event.candidateCount,
      event.targetRank ?? "missing",
    ].join("|"),
  );
}

function chooseEviction(
  points: MemoryPoint[],
  config: ExperimentConfig,
  random: () => number,
  effectiveCapacity: number,
  streamOrdinal: number,
  incoming: MemoryPoint,
  pinnedRecordId: string | null,
) {
  const retained = points.filter((point) => point.retained);
  const isProtected = (point: MemoryPoint) =>
    point.id === pinnedRecordId ||
    (config.defense === "criticality_retention" &&
      point.importance >= declaredImportanceThreshold);

  if (config.policy === "reservoir") {
    const previousSample = retained.filter((point) => point.id !== incoming.id);
    const sampledIndex = Math.floor(random() * streamOrdinal);
    const sampled =
      sampledIndex < effectiveCapacity
        ? previousSample[sampledIndex] ?? incoming
        : incoming;
    if (!isProtected(sampled)) return sampled;
    return (
      [...retained]
        .filter((point) => !isProtected(point))
        .sort(
          (a, b) =>
            a.importance - b.importance ||
            a.createdAt - b.createdAt ||
            a.id.localeCompare(b.id),
        )[0] ?? incoming
    );
  }

  let candidates = retained;
  const unprotected = candidates.filter((point) => !isProtected(point));
  if (unprotected.length > 0) {
    candidates = unprotected;
  }

  if (config.policy === "fifo") {
    return [...candidates].sort(
      (a, b) => a.createdAt - b.createdAt || a.id.localeCompare(b.id),
    )[0];
  }
  if (config.policy === "lru") {
    return [...candidates].sort(
      (a, b) => a.lastAccess - b.lastAccess || a.id.localeCompare(b.id),
    )[0];
  }
  if (config.policy === "importance") {
    return [...candidates].sort(
      (a, b) => a.importance - b.importance || a.createdAt - b.createdAt,
    )[0];
  }
  if (config.policy === "mmr") {
    const crowdingById = new Map(
      candidates.map((point) => [
        point.id,
        candidates.filter(
          (other) => other.id !== point.id && distance(point, other) < 8,
        ).length,
      ]),
    );
    return [...candidates].sort((a, b) => {
      const aCrowding = crowdingById.get(a.id) ?? 0;
      const bCrowding = crowdingById.get(b.id) ?? 0;
      return bCrowding - aCrowding || a.createdAt - b.createdAt;
    })[0];
  }

  const minimumAccess = Math.min(...candidates.map((point) => point.lastAccess));
  const maximumAccess = Math.max(...candidates.map((point) => point.lastAccess));
  const accessRange = Math.max(1, maximumAccess - minimumAccess);
  const retentionScore = (point: MemoryPoint) => {
    const nearby = candidates.filter(
      (other) => other.id !== point.id && distance(point, other) < 12,
    ).length;
    const uniqueness =
      1 - clamp(nearby / Math.max(1, candidates.length - 1), 0, 1);
    const recency = clamp(
      (point.lastAccess - minimumAccess) / accessRange,
      0,
      1,
    );
    return point.importance * 0.5 + recency * 0.25 + uniqueness * 0.25;
  };
  const retentionScores = new Map(
    candidates.map((point) => [point.id, retentionScore(point)]),
  );
  return [...candidates].sort((a, b) => {
    return (
      (retentionScores.get(a.id) ?? 0) -
        (retentionScores.get(b.id) ?? 0) ||
      a.createdAt - b.createdAt ||
      a.id.localeCompare(b.id)
    );
  })[0];
}

function attackKnowledgeAim(
  config: ExperimentConfig,
  target: MemoryPoint,
  query: RetrievalQuery,
  step: number,
) {
  const progress = clamp(step / Math.max(1, config.budget), 0, 1);
  if (config.knowledge === "zero") {
    return { x: 52, y: 50, spread: 28 };
  }
  if (config.knowledge === "query") {
    return { x: query.x, y: query.y, spread: 14 };
  }
  if (config.knowledge === "concept") {
    const conceptOffset: Record<Domain, { x: number; y: number }> = {
      travel: { x: 3, y: -2 },
      healthcare: { x: -3, y: 2 },
      operations: { x: 2, y: 3 },
      finance: { x: -2, y: -3 },
    };
    const offset = conceptOffset[config.domain];
    return {
      x: target.x + offset.x,
      y: target.y + offset.y,
      spread: 9,
    };
  }
  if (config.knowledge === "black_box") {
    const learnedFraction = 0.45 + progress * 0.4;
    return {
      x: 52 + (query.x - 52) * learnedFraction,
      y: 50 + (query.y - 50) * learnedFraction,
      spread: 11 - progress * 5,
    };
  }
  return { x: query.x, y: query.y, spread: 3 };
}

function makeIncomingPoint(
  step: number,
  config: ExperimentConfig,
  random: () => number,
  target: MemoryPoint,
  query: RetrievalQuery,
) {
  const fragmentList = benignFragments[config.domain];
  const fragment = fragmentList[(step - 1) % fragmentList.length];
  const aim = attackKnowledgeAim(config, target, query, step);
  let x = 8 + random() * 84;
  let y = 8 + random() * 78;
  let origin = "legitimate-stream";

  if (config.attack === "same_domain") {
    x = aim.x + 7 + (random() - 0.5) * (16 + aim.spread * 0.35);
    y = aim.y + 6 + (random() - 0.5) * (16 + aim.spread * 0.35);
    origin = "domain-stream";
  }
  if (config.attack === "semantic_nearest") {
    x = aim.x + (random() - 0.5) * aim.spread;
    y = aim.y + (random() - 0.5) * aim.spread;
    origin = "topic-stream";
  }
  if (config.attack === "diverse") {
    const angle = step * 2.399963;
    const radius = 5 + (step % 5) * 2.6 + aim.spread * 0.18;
    x = aim.x + Math.cos(angle) * radius;
    y = aim.y + Math.sin(angle) * radius;
    origin = `diverse-${step % 4}`;
  }
  if (config.attack === "sybil") {
    const angle = step * 1.73;
    const radius = 4 + (step % 4) + aim.spread * 0.12;
    x = aim.x + Math.cos(angle) * radius;
    y = aim.y + Math.sin(angle) * radius;
    origin = `origin-${String(step).padStart(3, "0")}`;
  }
  if (config.attack === "adaptive") {
    const progress = clamp(step / Math.max(1, config.budget), 0, 1);
    const angle = step * 0.91 + progress * 1.7;
    const radius = 3 + aim.spread * (0.34 - progress * 0.16);
    x = aim.x + Math.cos(angle) * radius;
    y = aim.y + Math.sin(angle) * radius;
    origin = `adaptive-${step % 5}`;
  }

  const kind = config.attack === "none" ? "background" : "chaff";
  return makePoint({
    id: `${kind}-${String(step).padStart(3, "0")}`,
    content: `${fragment}. Record ${step} is benign and contains no instruction`,
    kind,
    origin,
    x: clamp(x, 4, 96),
    y: clamp(y, 5, 94),
    importance:
      kind === "background"
        ? 0.42 + random() * 0.38
        : 0.35 + random() * 0.46,
    createdAt: step,
    lastAccess: step,
  });
}

function shouldReject(
  incoming: MemoryPoint,
  retained: MemoryPoint[],
  config: ExperimentConfig,
  alertScore: number,
) {
  if (config.defense === "duplicate_control") {
    const nearDuplicate = retained.some(
      (point) => distance(point, incoming) < 2.7,
    );
    if (nearDuplicate) {
      return "Rejected because a near-duplicate already occupies this semantic region";
    }
  }

  if (config.defense === "origin_quota") {
    const originCount = retained.filter(
      (point) => point.origin === incoming.origin,
    ).length;
    const quota = Math.max(2, Math.floor(config.capacity / 5));
    if (originCount >= quota) {
      return `Rejected because origin quota ${quota} is already occupied`;
    }
  }

  if (config.defense === "semantic_coverage") {
    const cellCount = retained.filter(
      (point) => point.cell === incoming.cell,
    ).length;
    const cellQuota = Math.max(2, Math.ceil(config.capacity / 8));
    if (cellCount >= cellQuota) {
      return `Rejected because semantic cell ${incoming.cell} reached coverage quota`;
    }
  }

  if (config.defense === "canary_adaptive" && alertScore >= 0.58) {
    const localPressure = retained.filter(
      (point) => distance(point, incoming) < 10,
    ).length;
    if (localPressure >= Math.max(2, Math.floor(config.topK / 2))) {
      return "Rejected after the crowding monitor tightened local write admission";
    }
  }

  return null;
}

function evaluateQuery(
  points: MemoryPoint[],
  target: MemoryPoint,
  query: RetrievalQuery,
  config: ExperimentConfig,
  step: number,
) {
  const retained = points.filter((point) => point.retained);
  const ranked = [...retained].sort(
    (a, b) =>
      distance(a, query) - distance(b, query) || a.id.localeCompare(b.id),
  );
  const ranks = new Map(
    ranked.map((point, index) => [point.id, index + 1] as const),
  );
  const targetIndex = ranked.findIndex((point) => point.id === target.id);
  const rank = targetIndex < 0 ? null : targetIndex + 1;

  for (const point of points) {
    point.currentRank = point.retained ? (ranks.get(point.id) ?? null) : null;
  }
  const retrieved = ranked.slice(0, config.topK);
  for (const point of retrieved) {
    point.lastAccess = step;
  }

  const recall = rank !== null && rank <= config.topK ? 1 : 0;
  const actionReadLimit = Math.min(3, config.topK);
  const downstreamAvailable =
    rank !== null && rank <= actionReadLimit ? 1 : 0;
  const localDensity = clamp(
    retained.filter((point) => distance(point, query) <= 12).length /
      Math.max(4, config.topK * 2),
    0,
    1,
  );
  let nearPairs = 0;
  let possiblePairs = 0;
  for (let left = 0; left < retrieved.length; left += 1) {
    for (let right = left + 1; right < retrieved.length; right += 1) {
      possiblePairs += 1;
      if (distance(retrieved[left], retrieved[right]) < 4) {
        nearPairs += 1;
      }
    }
  }
  const nearDuplicateShare =
    possiblePairs === 0 ? 0 : nearPairs / possiblePairs;
  const originCounts = new Map<string, number>();
  for (const point of retrieved) {
    originCounts.set(point.origin, (originCounts.get(point.origin) ?? 0) + 1);
  }
  const dominantOriginShare =
    retrieved.length === 0
      ? 0
      : Math.max(0, ...originCounts.values()) / retrieved.length;
  const alertScore = clamp(
    0.05 +
      localDensity * 0.45 +
      nearDuplicateShare * 0.3 +
      dominantOriginShare * 0.15,
    0.05,
    0.95,
  );
  return {
    rank,
    recall,
    downstreamAvailable,
    alertScore,
    retainedCount: retained.length,
  };
}

function snapshotMemory(points: MemoryPoint[], step: number): MemoryStepState {
  const retained = points.filter((point) => point.retained);
  return {
    step,
    retainedIds: retained.map((point) => point.id),
    ranks: Object.fromEntries(
      retained.flatMap((point) =>
        point.currentRank === null ? [] : [[point.id, point.currentRank]],
      ),
    ),
  };
}

function summarizeMetrics(
  trajectory: TrajectoryPoint[],
  acceptedWrites: number,
  rejectedWrites: number,
): RunMetrics {
  const attacked = trajectory.slice(1);
  const evaluationWindow = attacked.length > 0 ? attacked : trajectory;
  const divisor = Math.max(1, evaluationWindow.length);
  const writesToFailure =
    evaluationWindow.find((point) => point.recall === 0)?.step ?? null;
  const final = trajectory[trajectory.length - 1];
  return {
    criticalRecall:
      evaluationWindow.reduce((sum, point) => sum + point.recall, 0) / divisor,
    physicalAvailability:
      evaluationWindow.reduce((sum, point) => sum + point.physical, 0) / divisor,
    downstreamAvailability:
      evaluationWindow.reduce(
        (sum, point) => sum + point.downstreamAvailable,
        0,
      ) /
      divisor,
    finalTargetRank: final.rank,
    writesToFailure,
    acceptedWrites,
    rejectedWrites,
    peakAlertScore: Math.max(
      ...trajectory.map((point) => point.alertScore),
    ),
  };
}

export function runSimulation(
  sourceConfig: ExperimentConfig,
  options: { capacityOverride?: number; pinned?: boolean } = {},
): RunResult {
  const config: ExperimentConfig = {
    ...sourceConfig,
    capacity: clamp(Math.round(sourceConfig.capacity), 1, 120),
    topK: clamp(Math.round(sourceConfig.topK), 1, 20),
    budget: clamp(Math.round(sourceConfig.budget), 0, 160),
    seed: Math.max(0, Math.round(sourceConfig.seed)),
  };
  const effectiveCapacity = Math.max(
    1,
    Math.round(options.capacityOverride ?? config.capacity),
  );
  const pinned = options.pinned ?? false;
  const backgroundRandom = purposeRandom(config.seed, "background");
  const trafficRandom = purposeRandom(config.seed, "traffic");
  const points: MemoryPoint[] = [];
  const trace: TraceDecision[] = [];
  const trajectory: TrajectoryPoint[] = [];
  const states: MemoryStepState[] = [];
  let previousHash = "0".repeat(32);
  let rejectedWrites = 0;
  let acceptedWrites = 0;
  const query = { ...queryByDomain[config.domain] };

  const target = makePoint({
    id: "critical-target",
    content: targetByDomain[config.domain],
    kind: "critical",
    origin: "verified-profile",
    x: 34,
    y: 43,
    importance: 0.8,
    createdAt: -100,
    lastAccess: -100,
  });
  points.push(target);

  const desiredBackgroundCount = Math.max(
    4,
    Math.floor(config.capacity * 0.54),
  );
  const backgroundCount = Math.min(
    desiredBackgroundCount,
    Math.max(0, config.capacity - 1),
    Math.max(0, effectiveCapacity - 1),
  );
  for (let index = 0; index < backgroundCount; index += 1) {
    const x = 8 + backgroundRandom() * 84;
    const y = 8 + backgroundRandom() * 80;
    points.push(
      makePoint({
        id: `background-${String(index + 1).padStart(2, "0")}`,
        content: benignFragments[config.domain][index % benignFragments[config.domain].length],
        kind: "background",
        origin: `session-${index % 3}`,
        x,
        y,
        importance: 0.4 + backgroundRandom() * 0.42,
        createdAt: -backgroundCount + index,
        lastAccess: -backgroundCount + index,
      }),
    );
  }

  const incomingPoints = Array.from({ length: config.budget }, (_, index) =>
    makeIncomingPoint(
      index + 1,
      config,
      trafficRandom,
      target,
      query,
    ),
  );

  let queryState = evaluateQuery(points, target, query, config, 0);
  const seedEvent = {
    step: 0,
    kind: "seed" as const,
    title: "Initialized bounded memory",
    reason: `Seeded one verified critical record and ${backgroundCount} legitimate records; retrieval uses a separate query vector`,
    recordId: target.id,
    candidateCount: points.length,
    targetRank: queryState.rank,
  };
  const seedHash = stableTraceHash(previousHash, seedEvent);
  trace.push({
    ...seedEvent,
    id: `event-${String(trace.length + 1).padStart(4, "0")}`,
    hash: seedHash,
    previousHash,
  });
  previousHash = seedHash;
  states.push(snapshotMemory(points, 0));

  trajectory.push({
    step: 0,
    recall: queryState.recall,
    physical: target.retained ? 1 : 0,
    rank: queryState.rank,
    downstreamAvailable: queryState.downstreamAvailable,
    occupancy: points.filter((point) => point.retained).length / effectiveCapacity,
    alertScore: queryState.alertScore,
    rejectedWrites,
    attackerCost: 0,
  });

  for (let step = 1; step <= config.budget; step += 1) {
    const incoming = incomingPoints[step - 1];
    const retainedBefore = points.filter((point) => point.retained);
    const rejectionReason = shouldReject(
      incoming,
      retainedBefore,
      config,
      queryState.alertScore,
    );

    if (rejectionReason) {
      rejectedWrites += 1;
      const defenseEvent = {
        step,
        kind: "defense" as const,
        title: "Write admission blocked",
        reason: rejectionReason,
        recordId: incoming.id,
        candidateCount: retainedBefore.length,
        targetRank: queryState.rank,
      };
      const defenseHash = stableTraceHash(previousHash, defenseEvent);
      trace.push({
        ...defenseEvent,
        id: `event-${String(trace.length + 1).padStart(4, "0")}`,
        hash: defenseHash,
        previousHash,
      });
      previousHash = defenseHash;
    } else {
      acceptedWrites += 1;
      points.push(incoming);
      const writeEvent = {
        step,
        kind: "write" as const,
        title: incoming.kind === "chaff" ? "Accepted benign chaff" : "Accepted benign traffic",
        reason: `${incoming.origin} wrote an audited, non-instructional record`,
        recordId: incoming.id,
        candidateCount: retainedBefore.length,
        targetRank: queryState.rank,
      };
      const writeHash = stableTraceHash(previousHash, writeEvent);
      trace.push({
        ...writeEvent,
        id: `event-${String(trace.length + 1).padStart(4, "0")}`,
        hash: writeHash,
        previousHash,
      });
      previousHash = writeHash;

      const retainedAfterWrite = points.filter((point) => point.retained);
      if (retainedAfterWrite.length > effectiveCapacity) {
        const evicted = chooseEviction(
          retainedAfterWrite,
          config,
          purposeRandom(config.seed, `eviction:${config.policy}:${step}`),
          effectiveCapacity,
          1 + backgroundCount + acceptedWrites,
          incoming,
          pinned ? target.id : null,
        );
        evicted.retained = false;
        evicted.currentRank = null;
        const evictionEvent = {
          step,
          kind: "eviction" as const,
          title: evicted.kind === "critical" ? "Critical record evicted" : "Capacity eviction",
          reason: `${policyLabels[config.policy]} selected ${evicted.id} at fixed capacity ${effectiveCapacity}`,
          recordId: evicted.id,
          candidateCount: retainedAfterWrite.length,
          targetRank: queryState.rank,
        };
        const evictionHash = stableTraceHash(previousHash, evictionEvent);
        trace.push({
          ...evictionEvent,
          id: `event-${String(trace.length + 1).padStart(4, "0")}`,
          hash: evictionHash,
          previousHash,
        });
        previousHash = evictionHash;
      }
    }

    queryState = evaluateQuery(points, target, query, config, step);
    const retrievalEvent = {
      step,
      kind: "retrieval" as const,
      title: queryState.recall ? "Critical memory retrieved" : "Critical memory unavailable",
      reason:
        queryState.rank === null
          ? "The target no longer exists in the bounded store"
          : `The separate query ranked the target ${queryState.rank} against a retrieval budget of ${config.topK}`,
      recordId: queryState.recall ? target.id : null,
      candidateCount: queryState.retainedCount,
      targetRank: queryState.rank,
    };
    const retrievalHash = stableTraceHash(previousHash, retrievalEvent);
    trace.push({
      ...retrievalEvent,
      id: `event-${String(trace.length + 1).padStart(4, "0")}`,
      hash: retrievalHash,
      previousHash,
    });
    previousHash = retrievalHash;
    states.push(snapshotMemory(points, step));

    trajectory.push({
      step,
      recall: queryState.recall,
      physical: target.retained ? 1 : 0,
      rank: queryState.rank,
      downstreamAvailable: queryState.downstreamAvailable,
      occupancy:
        points.filter((point) => point.retained).length / effectiveCapacity,
      alertScore: queryState.alertScore,
      rejectedWrites,
      attackerCost: step,
    });
  }

  const createdAt = new Date(0).toISOString();
  const digest = hash(
    JSON.stringify({
      previousHash,
      config,
      query,
      points,
      states,
      trajectory,
      acceptedWrites,
      rejectedWrites,
    }),
  );
  return {
    runId: `cm-${config.seed}-${digest}`,
    createdAt,
    config,
    query,
    points,
    states,
    trajectory,
    trace,
    metrics: summarizeMetrics(trajectory, acceptedWrites, rejectedWrites),
    digest,
  };
}

export function runComparison(config: ExperimentConfig): ComparisonArm[] {
  const undefended = runSimulation({ ...config, defense: "none" });
  const selected = runSimulation(config);
  const unlimited = runSimulation(
    { ...config, defense: "none" },
    { capacityOverride: Math.max(500, config.capacity + config.budget + 16) },
  );
  const pinned = runSimulation(
    { ...config, defense: "none" },
    { pinned: true },
  );
  return [
    {
      id: "undefended",
      label: "Matched undefended",
      description: "Same pre-generated traffic with no defense",
      metrics: undefended.metrics,
      trajectory: undefended.trajectory,
    },
    {
      id: "selected",
      label: "Selected defense",
      description: defenseLabels[config.defense],
      metrics: selected.metrics,
      trajectory: selected.trajectory,
    },
    {
      id: "unlimited",
      label: "Unlimited-storage control",
      description: "Storage control without fixed-capacity eviction",
      metrics: unlimited.metrics,
      trajectory: unlimited.trajectory,
    },
    {
      id: "pinned",
      label: "Gold-pin storage control",
      description: "Non-deployable control that pins the target in storage",
      metrics: pinned.metrics,
      trajectory: pinned.trajectory,
    },
  ];
}

export function resultToCsv(result: RunResult) {
  const header = [
    "step",
    "critical_recall",
    "physical_availability",
    "target_rank",
    "downstream_read_available",
    "capacity_utilization",
    "alert_score",
    "rejected_writes",
    "attacker_cost",
  ];
  const rows = result.trajectory.map((point) =>
    [
      point.step,
      point.recall,
      point.physical,
      point.rank ?? "",
      point.downstreamAvailable,
      point.occupancy.toFixed(6),
      point.alertScore.toFixed(6),
      point.rejectedWrites,
      point.attackerCost,
    ].join(","),
  );
  return [header.join(","), ...rows].join("\n");
}
