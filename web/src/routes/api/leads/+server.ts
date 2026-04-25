import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { createLead, listLeads } from '$lib/server/db';

export const GET: RequestHandler = async ({ url }) => {
	const outcome = (url.searchParams.get('outcome') ?? 'inbox') as
		| 'all'
		| 'inbox'
		| 'interested'
		| 'callback'
		| 'not_interested';
	const q = url.searchParams.get('q') ?? '';
	const offset = Number(url.searchParams.get('offset') ?? '0');
	const limit = Number(url.searchParams.get('limit') ?? '30');

	const data = await listLeads({ outcome, q, offset, limit });
	return json(data);
};

export const POST: RequestHandler = async ({ request }) => {
	const body = (await request.json()) as any;
	const id = await createLead({
		contact_name: String(body.contact_name ?? ''),
		contact_role: String(body.contact_role ?? ''),
		clinic_name: String(body.clinic_name ?? ''),
		clinic_size: String(body.clinic_size ?? ''),
		call_outcome: String(body.call_outcome ?? ''),
		next_action: String(body.next_action ?? ''),
		next_action_date: String(body.next_action_date ?? ''),
		notes: String(body.notes ?? ''),
		source_file: String(body.source_file ?? 'manual')
	});
	return json({ id });
};
