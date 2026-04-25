import { json } from '@sveltejs/kit';
import { getStats } from '$lib/server/db';

export async function GET() {
	return json(await getStats());
}
