import { json } from '@sveltejs/kit';
import { listCsvFiles } from '$lib/server/db';

export async function GET() {
	return json({ files: await listCsvFiles() });
}
