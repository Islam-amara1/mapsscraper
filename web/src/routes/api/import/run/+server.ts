import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { importAllResults, importCsvFile } from '$lib/server/db';

export const POST: RequestHandler = async ({ request }) => {
	const body = (await request.json().catch(() => ({}))) as any;
	const force = Boolean(body.force);
	const paths = Array.isArray(body.paths) ? body.paths.map(String) : null;
	const all = Boolean(body.all);

	if (all) {
		return json(await importAllResults(force));
	}

	if (paths && paths.length) {
		let files = 0;
		let rows = 0;
		for (const p of paths) {
			const r = await importCsvFile(p, force);
			if (r) files += 1;
			rows += r;
		}
		return json({ files, rows });
	}

	return json({ error: 'Nothing to import' }, { status: 400 });
};
