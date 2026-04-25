<script lang="ts">
	import { onMount } from 'svelte';

	type Outcome = 'all' | 'inbox' | 'interested' | 'callback' | 'not_interested';

	type Props = {
		outcome?: Outcome;
		title?: string;
		subtitle?: string;
	};

	let {
		outcome = 'inbox',
		title = 'Inbox',
		subtitle = 'Work through leads and log call outcomes.'
	}: Props = $props();

	type Lead = {
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

	type Stats = {
		total: number;
		inbox: number;
		callback: number;
		interested: number;
		not_interested: number;
	};

	let stats: Stats | null = $state(null);
	let q = $state('');
	let offset = $state(0);
	let limit = $state(30);
	let total = $state(0);
	let leads: Lead[] = $state([]);
	let selectedId: number | null = $state(null);
	let loading = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let edit: Partial<Lead> & { id?: number } = $state({});

	async function fetchStats() {
		const res = await fetch('/api/stats');
		stats = await res.json();
	}

	async function fetchLeads() {
		loading = true;
		error = null;
		try {
			const sp = new URLSearchParams();
			sp.set('outcome', outcome);
			if (q.trim()) sp.set('q', q.trim());
			sp.set('offset', String(offset));
			sp.set('limit', String(limit));
			const res = await fetch(`/api/leads?${sp.toString()}`);
			if (!res.ok) throw new Error(await res.text());
			const data = await res.json();
			total = Number(data.total ?? 0);
			leads = data.leads ?? [];
			if (leads.length) {
				if (!selectedId || !leads.some((l) => l.id === selectedId)) selectedId = leads[0].id;
				select(selectedId);
			} else {
				selectedId = null;
				edit = {};
			}
		} catch (e: any) {
			error = e?.message ?? String(e);
		} finally {
			loading = false;
		}
	}

	function select(id: number | null) {
		if (!id) return;
		selectedId = id;
		const lead = leads.find((l) => l.id === id);
		if (!lead) return;
		edit = { ...lead };
	}

	async function save() {
		if (!edit.id) return;
		saving = true;
		try {
			const res = await fetch(`/api/leads/${edit.id}`, {
				method: 'PATCH',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					contact_name: edit.contact_name ?? '',
					contact_role: edit.contact_role ?? '',
					clinic_name: edit.clinic_name ?? '',
					clinic_size: edit.clinic_size ?? '',
					call_outcome: edit.call_outcome ?? '',
					next_action: edit.next_action ?? '',
					next_action_date: edit.next_action_date ?? '',
					notes: edit.notes ?? ''
				})
			});
			if (!res.ok) throw new Error(await res.text());
			await fetchStats();
			await fetchLeads();
		} catch (e: any) {
			error = e?.message ?? String(e);
		} finally {
			saving = false;
		}
	}

	async function quickOutcome(value: '' | 'interested' | 'callback' | 'not_interested') {
		if (!edit.id) return;
		edit.call_outcome = value;
		await save();
	}

	async function remove() {
		if (!edit.id) return;
		if (!confirm('Delete this lead?')) return;
		const res = await fetch(`/api/leads/${edit.id}`, { method: 'DELETE' });
		if (!res.ok) {
			error = await res.text();
			return;
		}
		await fetchStats();
		await fetchLeads();
	}

	async function createNew() {
		const clinic = prompt('Clinic name')?.trim();
		if (!clinic) return;
		const res = await fetch('/api/leads', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ clinic_name: clinic, source_file: 'manual' })
		});
		if (!res.ok) {
			error = await res.text();
			return;
		}
		await fetchStats();
		await fetchLeads();
	}

	onMount(async () => {
		await fetchStats();
		await fetchLeads();
	});
</script>

<div class="space-y-6">
	<header class="flex flex-col justify-between gap-3 md:flex-row md:items-end">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-white">{title}</h1>
			<p class="mt-1 text-sm text-white/60">{subtitle}</p>
		</div>
		<div class="flex flex-wrap gap-2">
			<button
				class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
				onclick={createNew}
			>
				New lead
			</button>
			<a
				class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
				href="/imports"
			>
				Import CSVs
			</a>
		</div>
	</header>

	{#if stats}
		<div class="grid grid-cols-2 gap-3 md:grid-cols-5">
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="text-xs text-white/60">Total</div>
				<div class="mt-1 text-2xl font-semibold text-white">{stats.total}</div>
			</div>
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="text-xs text-white/60">Inbox</div>
				<div class="mt-1 text-2xl font-semibold text-white">{stats.inbox}</div>
			</div>
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="text-xs text-white/60">Callbacks</div>
				<div class="mt-1 text-2xl font-semibold text-white">{stats.callback}</div>
			</div>
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="text-xs text-white/60">Interested</div>
				<div class="mt-1 text-2xl font-semibold text-white">{stats.interested}</div>
			</div>
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="text-xs text-white/60">Not interested</div>
				<div class="mt-1 text-2xl font-semibold text-white">{stats.not_interested}</div>
			</div>
		</div>
	{/if}

	{#if error}
		<div class="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
			{error}
		</div>
	{/if}

	<div class="grid grid-cols-1 gap-6 lg:grid-cols-12">
		<section class="lg:col-span-7 xl:col-span-8">
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
					<div class="text-sm text-white/70">
						{#if loading}
							Loading…
						{:else}
							Showing <span class="text-white">{leads.length}</span> of
							<span class="text-white">{total}</span>
						{/if}
					</div>
					<div class="flex flex-wrap gap-2">
						<input
							class="w-64 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
							placeholder="Search clinic / contact / role"
							bind:value={q}
							onkeydown={(e) => {
								if (e.key === 'Enter') {
									offset = 0;
									void fetchLeads();
								}
							}}
						/>
						<select
							class="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
							bind:value={limit}
							onchange={() => {
								offset = 0;
								void fetchLeads();
							}}
						>
							<option value="20">20</option>
							<option value="30">30</option>
							<option value="50">50</option>
							<option value="100">100</option>
						</select>
						<button
							class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
							onclick={() => void fetchLeads()}
						>
							Refresh
						</button>
					</div>
				</div>

				<div class="mt-4 overflow-hidden rounded-xl border border-white/10">
					<table class="w-full text-left text-sm">
						<thead class="bg-black/30 text-xs tracking-wide text-white/60 uppercase">
							<tr>
								<th class="px-3 py-2">Clinic</th>
								<th class="px-3 py-2">Contact</th>
								<th class="px-3 py-2">Outcome</th>
								<th class="hidden px-3 py-2 md:table-cell">Next</th>
								<th class="hidden px-3 py-2 lg:table-cell">Date</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-white/10">
							{#each leads as l (l.id)}
								<tr
									class="cursor-pointer transition {l.id === selectedId
										? 'bg-white/10'
										: 'hover:bg-white/5'}"
									onclick={() => select(l.id)}
								>
									<td class="px-3 py-2 font-medium text-white">
										{l.clinic_name || 'Unnamed'}
										<div class="text-xs font-normal text-white/50">{l.clinic_size || '—'}</div>
									</td>
									<td class="px-3 py-2 text-white/80">
										{l.contact_name || '—'}
										<div class="text-xs text-white/50">{l.contact_role || '—'}</div>
									</td>
									<td class="px-3 py-2">
										<span
											class="inline-flex items-center rounded-full border border-white/10 bg-black/20 px-2 py-1 text-xs text-white/70"
											>{l.call_outcome || '—'}</span
										>
									</td>
									<td class="hidden px-3 py-2 text-white/70 md:table-cell"
										>{l.next_action || '—'}</td
									>
									<td class="hidden px-3 py-2 text-white/70 lg:table-cell"
										>{l.next_action_date || '—'}</td
									>
								</tr>
							{/each}
							{#if !leads.length && !loading}
								<tr>
									<td class="px-3 py-10 text-center text-white/60" colspan="5">No leads.</td>
								</tr>
							{/if}
						</tbody>
					</table>
				</div>

				<div class="mt-4 flex items-center justify-between">
					<button
						class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10 disabled:opacity-40"
						disabled={offset === 0}
						onclick={() => {
							offset = Math.max(0, offset - limit);
							void fetchLeads();
						}}
					>
						Prev
					</button>
					<div class="text-xs text-white/50">
						{#if total}
							Page {Math.floor(offset / limit) + 1} / {Math.max(1, Math.ceil(total / limit))}
						{/if}
					</div>
					<button
						class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10 disabled:opacity-40"
						disabled={offset + limit >= total}
						onclick={() => {
							offset = offset + limit;
							void fetchLeads();
						}}
					>
						Next
					</button>
				</div>
			</div>
		</section>

		<section class="lg:col-span-5 xl:col-span-4">
			<div class="rounded-2xl border border-white/10 bg-white/5 p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-semibold text-white">Editor</div>
						<div class="text-xs text-white/60">Log the call like a CRM.</div>
					</div>
					<div class="flex gap-2">
						<button
							class="rounded-xl border border-white/10 bg-black/20 px-2 py-1 text-xs text-white/70 hover:bg-white/10"
							onclick={() => quickOutcome('interested')}
							disabled={!edit.id || saving}
						>
							Interested
						</button>
						<button
							class="rounded-xl border border-white/10 bg-black/20 px-2 py-1 text-xs text-white/70 hover:bg-white/10"
							onclick={() => quickOutcome('callback')}
							disabled={!edit.id || saving}
						>
							Callback
						</button>
						<button
							class="rounded-xl border border-white/10 bg-black/20 px-2 py-1 text-xs text-white/70 hover:bg-white/10"
							onclick={() => quickOutcome('not_interested')}
							disabled={!edit.id || saving}
						>
							Not
						</button>
					</div>
				</div>

				{#if !edit.id}
					<div class="mt-6 text-sm text-white/60">Select a lead on the left.</div>
				{:else}
					<div class="mt-4 grid grid-cols-1 gap-3">
						<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
							<div>
								<label class="text-xs text-white/60" for="contact_name">Contact name</label>
								<input
									id="contact_name"
									class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
									bind:value={edit.contact_name}
								/>
							</div>
							<div>
								<label class="text-xs text-white/60" for="contact_role">Role</label>
								<input
									id="contact_role"
									class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
									bind:value={edit.contact_role}
								/>
							</div>
						</div>

						<div>
							<label class="text-xs text-white/60" for="clinic_name">Clinic name</label>
							<input
								id="clinic_name"
								class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
								bind:value={edit.clinic_name}
							/>
						</div>

						<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
							<div>
								<label class="text-xs text-white/60" for="clinic_size">Clinic size</label>
								<input
									id="clinic_size"
									class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
									bind:value={edit.clinic_size}
								/>
							</div>
							<div>
								<label class="text-xs text-white/60" for="call_outcome">Call outcome</label>
								<select
									id="call_outcome"
									class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
									bind:value={edit.call_outcome}
								>
									<option value="">—</option>
									<option value="interested">interested</option>
									<option value="callback">callback</option>
									<option value="not_interested">not_interested</option>
								</select>
							</div>
						</div>

						<div class="grid grid-cols-1 gap-3 md:grid-cols-2">
							<div>
								<label class="text-xs text-white/60" for="next_action">Next action</label>
								<input
									id="next_action"
									class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
									bind:value={edit.next_action}
								/>
							</div>
							<div>
								<label class="text-xs text-white/60" for="next_action_date">
									Next action date (YYYY-MM-DD)
								</label>
								<input
									id="next_action_date"
									class="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
									placeholder="2026-04-30"
									bind:value={edit.next_action_date}
								/>
							</div>
						</div>

						<div>
							<label class="text-xs text-white/60" for="notes">Notes</label>
							<textarea
								id="notes"
								class="mt-1 h-36 w-full resize-none rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
								bind:value={edit.notes}
							></textarea>
						</div>

						<div class="grid grid-cols-2 gap-3">
							<button
								class="rounded-xl bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40"
								disabled={saving}
								onclick={() => void save()}
							>
								{saving ? 'Saving…' : 'Save'}
							</button>
							<button
								class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
								onclick={remove}
							>
								Delete
							</button>
						</div>

						<div class="text-xs text-white/50">
							Source: <span class="text-white/70">{edit.source_file || '—'}</span>
						</div>
					</div>
				{/if}
			</div>
		</section>
	</div>
</div>
