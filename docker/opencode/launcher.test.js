"use strict";

const assert = require("node:assert/strict");
const { test } = require("node:test");

process.env.OPENCODE_LAUNCHER_TOKEN = "test-only-token";
process.env.KOSMO_OPENCODE_IMAGE = "example/opencode:fixed-sha";
process.env.KOSMO_STACK = "test";
process.env.KOSMO_NETWORK = "kosmo-test-network";
process.env.KOSMO_WORKSPACES_HOST_PATH = "/opt/kosmo/test/workspaces";

const { buildJobConfig, tarFile, validId, validModel } = require("./launcher");

test("job mounts one project and never exposes provider key in Docker metadata", () => {
  const config = buildJobConfig(
    { project_id: "prj_123", provider: "deepseek", model: "deepseek-flash", api_key: "sk-sensitive" },
    "one-time-password",
  );
  assert.equal(config.HostConfig.Memory, 1073741824);
  assert.equal(config.HostConfig.NanoCpus, 1500000000);
  assert.equal(config.HostConfig.ReadonlyRootfs, true);
  assert.deepEqual(config.HostConfig.Binds, [
    "/opt/kosmo/test/workspaces/prj_123:/workspaces/prj_123:rw",
    "/opt/kosmo/test/workspaces/prj_123/opencode.json:/workspaces/prj_123/opencode.json:ro",
  ]);
  assert.ok(config.Env.includes("OPENCODE_MODEL=deepseek/deepseek-flash"));
  assert.ok(!JSON.stringify(config).includes("sk-sensitive"));
  assert.ok(!config.Env.some((value) => value.startsWith("DEEPSEEK_API_KEY=")));
  assert.ok(config.HostConfig.Tmpfs["/run/kosmo-secrets"].includes("size=1m"));
});

test("secret tar entry is owned by the unprivileged job user with mode 0600", () => {
  const archive = tarFile("provider-key", "sk-sensitive");
  const readOctal = (start, length) => parseInt(archive.toString("ascii", start, start + length), 8);
  assert.equal(readOctal(100, 8), 0o600);
  assert.equal(readOctal(108, 8), 1000);
  assert.equal(readOctal(116, 8), 1000);
  assert.equal(archive.toString("utf8", 512, 524), "sk-sensitive");
  archive.fill(0);
});

test("only safe project and model identifiers are accepted", () => {
  assert.equal(validId("prj_123"), true);
  assert.equal(validId("../secrets"), false);
  assert.equal(validModel("deepseek-flash"), true);
  assert.equal(validModel("model;cat /etc/passwd"), false);
});
