import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { deleteLead, getLead, updateLead } from '$lib/server/db';

export const GET: RequestHandler = async ({ params }) => {
	const id = Number(params.id);
	const lead = await getLead(id);
	if (!lead) return json({ error: 'Not found' }, { status: 404 });
	return json(lead);
};

export const PATCH: RequestHandler = async ({ params, request }) => {
	const id = Number(params.id);
	const patch = (await request.json()) as any;
	await updateLead(id, patch);
	return json({ ok: true });
};

export const DELETE: RequestHandler = async ({ params }) => {
	const id = Number(params.id);
	await deleteLead(id);
	return json({ ok: true });
};
