import { execSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const UPDATE_URL =
	"https://cursor.com/api/download?platform=linux-x64&releaseTrack=stable";

const __dirname = dirname(fileURLToPath(import.meta.url));

interface VersionInfo {
	version: string;
	commit: string;
	url: string;
}

async function getLatestVersion(): Promise<VersionInfo> {
	try {
		const resp = await fetch(UPDATE_URL, {
			headers: { "User-Agent": "cursor-ide-updater/1.0" },
			signal: AbortSignal.timeout(30_000),
		});
		const data = await resp.json();

		if (data.version && data.commitSha) {
			return {
				version: data.version,
				commit: data.commitSha,
				url: data.debUrl ?? "",
			};
		}

		if (data.name && data.version) {
			return {
				version: data.name,
				commit: data.version,
				url: data.url ?? "",
			};
		}
	} catch (e) {
		console.error(`Update API failed: ${e}`);
	}

	console.error("ERROR: Could not determine latest Cursor version.");
	return process.exit(1);
}

function getCurrentVersion(pkgbuildPath: string): {
	version: string;
	commit: string;
} {
	const text = readFileSync(pkgbuildPath, "utf-8");
	const verMatch = text.match(/^pkgver=(.+)$/m);
	const commitMatch = text.match(/^_commit=(.+)$/m);
	if (!verMatch || !commitMatch) {
		console.error("ERROR: Could not parse pkgver/_commit from PKGBUILD");
		process.exit(1);
	}
	return { version: verMatch[1].trim(), commit: commitMatch[1].trim() };
}

async function computeSha256(url: string): Promise<string> {
	console.error(`Downloading ${url} for checksum...`);
	const resp = await fetch(url, {
		headers: { "User-Agent": "cursor-ide-updater/1.0" },
		signal: AbortSignal.timeout(300_000),
	});
	if (!resp.ok || !resp.body) {
		throw new Error(`Download failed: ${resp.status} ${resp.statusText}`);
	}
	const hash = createHash("sha256");
	for await (const chunk of resp.body) {
		hash.update(chunk);
	}
	return hash.digest("hex");
}

function updatePkgbuild(
	pkgbuildPath: string,
	newVer: string,
	newCommit: string,
	newSha256: string,
): void {
	let text = readFileSync(pkgbuildPath, "utf-8");
	text = text.replace(/^pkgver=.+$/m, `pkgver=${newVer}`);
	text = text.replace(/^pkgrel=.+$/m, "pkgrel=1");
	text = text.replace(/^_commit=.+$/m, `_commit=${newCommit}`);
	text = text.replace(/(sha256sums=\(')[^']*(')/, `$1${newSha256}$2`);
	writeFileSync(pkgbuildPath, text);
}

function generateSrcinfo(pkgbuildDir: string): string {
	const result = execSync("makepkg --printsrcinfo", {
		cwd: pkgbuildDir,
		encoding: "utf-8",
	});
	return result;
}

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const check = args.includes("--check");
	const update = args.includes("--update");
	const skipChecksum = args.includes("--skip-checksum");

	if (!check && !update) {
		console.error(
			"Usage: npx tsx update.ts [--check | --update] [--skip-checksum]",
		);
		process.exit(1);
	}

	const pkgbuildArg = args.find((a) => a.startsWith("--pkgbuild="));
	const pkgbuildPath = pkgbuildArg
		? pkgbuildArg.split("=")[1]
		: join(__dirname, "PKGBUILD");

	const latest = await getLatestVersion();
	const current = getCurrentVersion(pkgbuildPath);

	console.error(
		`Current: ${current.version} (${current.commit.slice(0, 12)}...)`,
	);
	console.error(
		`Latest:  ${latest.version} (${latest.commit.slice(0, 12)}...)`,
	);

	if (check) {
		const isNew =
			latest.version !== current.version || latest.commit !== current.commit;
		const out = {
			current_version: current.version,
			latest_version: latest.version,
			latest_commit: latest.commit,
			update_available: isNew,
		};
		console.log(JSON.stringify(out, null, 2));
		return;
	}

	if (update) {
		if (
			latest.version === current.version &&
			latest.commit === current.commit
		) {
			console.error("Already up-to-date.");
			process.exit(2);
		}

		const debUrl = `https://downloads.cursor.com/production/${latest.commit}/linux/x64/deb/amd64/deb/cursor_${latest.version}_amd64.deb`;
		let sha256: string;
		if (skipChecksum) {
			sha256 = "SKIP";
		} else {
			sha256 = await computeSha256(debUrl);
			console.error(`SHA256: ${sha256}`);
		}

		updatePkgbuild(pkgbuildPath, latest.version, latest.commit, sha256);
		console.error(`PKGBUILD updated to ${latest.version}`);

		const pkgbuildDir = dirname(pkgbuildPath);
		const srcinfoPath = join(pkgbuildDir, ".SRCINFO");
		try {
			const srcinfo = generateSrcinfo(pkgbuildDir);
			writeFileSync(srcinfoPath, srcinfo);
			console.error(".SRCINFO regenerated");
		} catch (e) {
			console.error(`Warning: Could not regenerate .SRCINFO: ${e}`);
			console.error(
				"You may need to run 'makepkg --printsrcinfo > .SRCINFO' manually.",
			);
		}
	}
}

main();
