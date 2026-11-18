/* Browser acceptance smoke for the synthetic tracker. */
const fs = require("node:fs");
const assert = require("node:assert/strict");
const { chromium } = require(process.env.TRACKER_PLAYWRIGHT);

async function main() {
  const accounts = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(10000);
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto("http://127.0.0.1:8090/");
    async function signIn(role) {
      await page.getByLabel("Workspace token").fill(accounts.find((account) => account.role === role).token);
      await page.getByRole("button", { name: "Open workspace" }).click();
    }
    await signIn("contributor");
    await page.getByLabel("Title").fill("Browser exercise");
    await page.getByLabel("Evidence note").fill("Fictional access review note.");
    await page.getByRole("button", { name: "Submit for review" }).click();
    await page.getByText("Evidence submitted for review.").waitFor();
    await page.getByRole("button", { name: "Sign out" }).click();
    await signIn("reviewer");
    const record = page.getByRole("article").filter({ hasText: "Browser exercise" });
    await record.getByLabel("Review rationale").fill("Verified against the synthetic checklist.");
    await record.getByRole("button", { name: "Record decision" }).click();
    await page.getByText("Decision recorded.").waitFor();
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Export audit history" }).click(),
    ]);
    const data = JSON.parse(fs.readFileSync(await download.path(), "utf8"));
    assert.equal(data.records.find((item) => item.title === "Browser exercise").status, "approved");
    assert.equal(data.events.at(-1).kind, "exported");
    assert.deepEqual(errors, []);
    fs.writeFileSync(process.argv[3], JSON.stringify({ passed: true, checks: ["submit", "review", "download"] }) + "\n");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
