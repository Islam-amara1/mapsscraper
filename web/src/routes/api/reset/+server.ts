import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { ensureSchema, resetDb } from '$lib/server/db';
import { rm } from 'node:fs/promises';

const dbFileUrl = new URL('../../../../../data/crm.db', import.meta.url);

export const POST: RequestHandler = async ({ request }) => {
	const body = (await request.json().catch(() => ({}))) as any;
	if (body.confirm !== 'RESET') {
		return json({ error: "Send { confirm: 'RESET' }" }, { status: 400 });
	}

	await resetDb();

	try {
		await rm(dbFileUrl.pathname);
	} catch {
		// ignore
	}

	await ensureSchema();

	return json({ ok: true });
};
