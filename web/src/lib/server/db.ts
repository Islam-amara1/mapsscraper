import { createClient, type Client } from '@libsql/client';
import { readFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { basename } from 'node:path';
import { parse } from 'csv-parse/sync';

const dbFileUrl = new URL('../../../../data/crm.db', import.meta.url);
const resultsDirUrl = new URL('../../../../data/results/', import.meta.url);

let client: Client | null = null;
let schemaReady = false;

function dbUrl(): string {
	const path = dbFileUrl.pathname;
	return `file:${path}`;
}

export function getDb(): Client {
	if (!client) {
		client = createClient({ url: dbUrl() });
	}
	return client;
}

export async function resetDb(): Promise<void> {
	try {
		// @libsql/client exposes close() in recent versions; keep optional.
		await (client as any)?.close?.();
	} catch {
		// ignore
	}
	client = null;
	schemaReady = false;
}

export async function ensureSchema(): Promise<void> {
	if (schemaReady) return;
	const db = getDb();
	await db.execute(`
		CREATE TABLE IF NOT EXISTS imports (
			source_file TEXT PRIMARY KEY,
			file_mtime REAL,
			row_count INTEGER,
			imported_at TEXT
		)
	`);
	await db.execute(`
		CREATE TABLE IF NOT EXISTS leads (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			contact_name TEXT,
			contact_role TEXT,
			clinic_name TEXT,
			clinic_size TEXT,
			call_outcome TEXT,
			next_action TEXT,
			next_action_date TEXT,
			notes TEXT,
			source_file TEXT,
			created_at TEXT DEFAULT CURRENT_TIMESTAMP,
			updated_at TEXT DEFAULT CURRENT_TIMESTAMP
		)
	`);
	schemaReady = true;
}

export type Lead = {
	id: number;
	contact_name: string;
	contact_role: string;
	clinic_name: string;
	clinic_size: string;
	call_outcome: string;
	next_action: string;
	next_action_date: string;
	notes: string;
	source_file: string;
	created_at: string;
	updated_at: string;
};

export type LeadUpdate = Partial<
	Pick<
		Lead,
		| 'contact_name'
		| 'contact_role'
		| 'clinic_name'
		| 'clinic_size'
		| 'call_outcome'
		| 'next_action'
		| 'next_action_date'
		| 'notes'
	>
>;

function rowToLead(row: any): Lead {
	return {
		id: Number(row.id),
		contact_name: String(row.contact_name ?? ''),
		contact_role: String(row.contact_role ?? ''),
		clinic_name: String(row.clinic_name ?? ''),
		clinic_size: String(row.clinic_size ?? ''),
		call_outcome: String(row.call_outcome ?? ''),
		next_action: String(row.next_action ?? ''),
		next_action_date: String(row.next_action_date ?? ''),
		notes: String(row.notes ?? ''),
		source_file: String(row.source_file ?? ''),
		created_at: String(row.created_at ?? ''),
		updated_at: String(row.updated_at ?? '')
	};
}

export async function getStats(): Promise<{
	total: number;
	inbox: number;
	callback: number;
	interested: number;
	not_interested: number;
}> {
	await ensureSchema();
	const db = getDb();
	const res = await db.execute(`
		SELECT
			COUNT(*) as total,
			SUM(CASE WHEN (call_outcome IS NULL OR TRIM(call_outcome) = '') THEN 1 ELSE 0 END) as inbox,
			SUM(CASE WHEN call_outcome = 'callback' THEN 1 ELSE 0 END) as callback,
			SUM(CASE WHEN call_outcome = 'interested' THEN 1 ELSE 0 END) as interested,
			SUM(CASE WHEN call_outcome = 'not_interested' THEN 1 ELSE 0 END) as not_interested
		FROM leads
	`);
	const row = res.rows[0] ?? {};
	return {
		total: Number((row as any).total ?? 0),
		inbox: Number((row as any).inbox ?? 0),
		callback: Number((row as any).callback ?? 0),
		interested: Number((row as any).interested ?? 0),
		not_interested: Number((row as any).not_interested ?? 0)
	};
}

export async function listLeads(opts: {
	outcome?: 'all' | 'inbox' | 'interested' | 'callback' | 'not_interested';
	q?: string;
	offset?: number;
	limit?: number;
}): Promise<{ total: number; leads: Lead[] }> {
	await ensureSchema();
	const db = getDb();

	const outcome = opts.outcome ?? 'inbox';
	const q = (opts.q ?? '').trim().toLowerCase();
	const offset = Math.max(0, Number(opts.offset ?? 0));
	const limit = Math.min(200, Math.max(10, Number(opts.limit ?? 30)));

	const where: string[] = [];
	const args: any[] = [];

	if (outcome === 'inbox') {
		where.push(`(call_outcome IS NULL OR TRIM(call_outcome) = '')`);
	} else if (outcome !== 'all') {
		where.push(`call_outcome = ?`);
		args.push(outcome);
	}

	if (q) {
		where.push(
			`(LOWER(COALESCE(clinic_name,'')) LIKE ? OR LOWER(COALESCE(contact_name,'')) LIKE ? OR LOWER(COALESCE(contact_role,'')) LIKE ?)`
		);
		args.push(`%${q}%`, `%${q}%`, `%${q}%`);
	}

	const whereSql = where.length ? `WHERE ${where.join(' AND ')}` : '';

	const totalRes = await db.execute({
		sql: `SELECT COUNT(*) as c FROM leads ${whereSql}`,
		args
	});
	const total = Number((totalRes.rows[0] as any)?.c ?? 0);

	const listRes = await db.execute({
		sql: `
			SELECT * FROM leads
			${whereSql}
			ORDER BY updated_at DESC, created_at DESC
			LIMIT ? OFFSET ?
		`,
		args: [...args, limit, offset]
	});

	return { total, leads: listRes.rows.map(rowToLead) };
}

export async function getLead(id: number): Promise<Lead | null> {
	await ensureSchema();
	const db = getDb();
	const res = await db.execute({ sql: `SELECT * FROM leads WHERE id = ? LIMIT 1`, args: [id] });
	const row = res.rows[0];
	return row ? rowToLead(row) : null;
}

export async function createLead(
	lead: Omit<Lead, 'id' | 'created_at' | 'updated_at'>
): Promise<number> {
	await ensureSchema();
	const db = getDb();
	const res = await db.execute({
		sql: `
			INSERT INTO leads (
				contact_name, contact_role, clinic_name, clinic_size,
				call_outcome, next_action, next_action_date, notes, source_file,
				updated_at
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
		`,
		args: [
			lead.contact_name ?? '',
			lead.contact_role ?? '',
			lead.clinic_name ?? '',
			lead.clinic_size ?? '',
			lead.call_outcome ?? '',
			lead.next_action ?? '',
			lead.next_action_date ?? '',
			lead.notes ?? '',
			lead.source_file ?? 'manual'
		]
	});
	return Number(res.lastInsertRowid);
}

export async function updateLead(id: number, patch: LeadUpdate): Promise<void> {
	await ensureSchema();
	const db = getDb();
	const fields: string[] = [];
	const args: any[] = [];
	for (const [k, v] of Object.entries(patch)) {
		if (v === undefined) continue;
		fields.push(`${k} = ?`);
		args.push(typeof v === 'string' ? v : String(v));
	}
	fields.push(`updated_at = CURRENT_TIMESTAMP`);
	args.push(id);
	await db.execute({ sql: `UPDATE leads SET ${fields.join(', ')} WHERE id = ?`, args });
}

export async function deleteLead(id: number): Promise<void> {
	await ensureSchema();
	const db = getDb();
	await db.execute({ sql: `DELETE FROM leads WHERE id = ?`, args: [id] });
}

export type ImportFile = {
	path: string;
	name: string;
	imported: boolean;
	mtimeMs: number;
	size: number;
};

export async function listCsvFiles(): Promise<ImportFile[]> {
	await ensureSchema();
	const resultsDirPath = resultsDirUrl.pathname;
	if (!existsSync(resultsDirPath)) return [];

	const { readdir, stat } = await import('node:fs/promises');
	const entries = await readdir(resultsDirPath);
	const csvs = entries.filter((e) => e.toLowerCase().endsWith('.csv'));

	const importedSet = new Set<string>();
	const db = getDb();
	const imp = await db.execute(`SELECT source_file FROM imports`);
	for (const r of imp.rows) importedSet.add(String((r as any).source_file ?? ''));

	const files: ImportFile[] = [];
	for (const name of csvs) {
		const fullPath = new URL(`./${name}`, resultsDirUrl).pathname;
		const s = await stat(fullPath);
		files.push({
			path: fullPath,
			name,
			imported: importedSet.has(fullPath),
			mtimeMs: s.mtimeMs,
			size: s.size
		});
	}
	files.sort((a, b) => b.mtimeMs - a.mtimeMs);
	return files;
}

async function markImported(
	source_file: string,
	file_mtime: number | null,
	row_count: number
): Promise<void> {
	await ensureSchema();
	const db = getDb();
	await db.execute({
		sql: `
			INSERT OR REPLACE INTO imports (source_file, file_mtime, row_count, imported_at)
			VALUES (?, ?, ?, CURRENT_TIMESTAMP)
		`,
		args: [source_file, file_mtime, row_count]
	});
}

async function deleteLeadsBySource(source_file: string): Promise<void> {
	await ensureSchema();
	const db = getDb();
	await db.execute({ sql: `DELETE FROM leads WHERE source_file = ?`, args: [source_file] });
}

export async function importCsvFile(sourcePath: string, force: boolean): Promise<number> {
	await ensureSchema();
	const db = getDb();

	const already = await db.execute({
		sql: `SELECT 1 FROM imports WHERE source_file = ? LIMIT 1`,
		args: [sourcePath]
	});
	if (already.rows.length && !force) return 0;
	if (force) await deleteLeadsBySource(sourcePath);

	const raw = await readFile(sourcePath);
	const text = raw.toString('utf8').replace(/^\uFEFF/, '');
	const records = parse(text, { columns: true, skip_empty_lines: true, relax_column_count: true });

	let count = 0;
	for (const r of records as any[]) {
		const clinic_name = String(r.clinic_name ?? r.name ?? r.business_name ?? '').trim();
		const contact_name = String(r.contact_name ?? '').trim();
		const contact_role = String(r.contact_role ?? '').trim();
		const clinic_size = String(r.clinic_size ?? '').trim();
		const call_outcome = String(r.call_outcome ?? '').trim();
		const next_action = String(r.next_action ?? '').trim();
		const next_action_date = String(r.next_action_date ?? '').trim();

		const address = String(r.address ?? '').trim();
		const phone = String(r.phone ?? '').trim();
		const website = String(r.website ?? '').trim();
		const maps = String(r.google_maps_url ?? '').trim();
		const category = String(r.category ?? '').trim();

		let notes = String(r.notes ?? '').trim();
		if (!notes) {
			const parts: string[] = [];
			if (address) parts.push(`Address: ${address}`);
			if (phone) parts.push(`Phone: ${phone}`);
			if (website) parts.push(`Website: ${website}`);
			if (maps) parts.push(`Maps: ${maps}`);
			if (category) parts.push(`Category: ${category}`);
			notes = parts.join('\n');
		}

		await db.execute({
			sql: `
				INSERT INTO leads (
					contact_name, contact_role, clinic_name, clinic_size,
					call_outcome, next_action, next_action_date, notes, source_file,
					updated_at
				) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
			`,
			args: [
				contact_name,
				contact_role,
				clinic_name,
				clinic_size,
				call_outcome,
				next_action,
				next_action_date,
				notes,
				sourcePath
			]
		});
		count += 1;
	}

	let mtime: number | null = null;
	try {
		const { stat } = await import('node:fs/promises');
		mtime = (await stat(sourcePath)).mtimeMs;
	} catch {
		// ignore
	}
	await markImported(sourcePath, mtime, count);
	return count;
}

export async function importAllResults(force: boolean): Promise<{ files: number; rows: number }> {
	const files = await listCsvFiles();
	let importedFiles = 0;
	let importedRows = 0;
	for (const f of files) {
		const rows = await importCsvFile(f.path, force);
		if (rows) {
			importedFiles += 1;
			importedRows += rows;
		}
	}
	return { files: importedFiles, rows: importedRows };
}

export function displayPath(p: string): string {
	return basename(p);
}
