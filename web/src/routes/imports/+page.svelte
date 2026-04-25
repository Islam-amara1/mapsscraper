<script lang="ts">
	import { onMount } from 'svelte';

	type ImportFile = {
		path: string;
		name: string;
		imported: boolean;
		mtimeMs: number;
		size: number;
	};

	let files: ImportFile[] = $state([]);
	let selected = $state<Record<string, boolean>>({});
	let force = $state(false);
	let loading = $state(false);
	let message = $state<string | null>(null);

	async function refresh() {
		loading = true;
		message = null;
		const res = await fetch('/api/import/files');
		const data = await res.json();
		files = data.files ?? [];
		const next: Record<string, boolean> = {};
		for (const f of files) next[f.path] = selected[f.path] ?? !f.imported;
		selected = next;
		loading = false;
	}

	function humanBytes(n: number) {
		const units = ['B', 'KB', 'MB', 'GB'];
		let v = n;
		let i = 0;
		while (v >= 1024 && i < units.length - 1) {
			v /= 1024;
			i += 1;
		}
		return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
	}

	async function run(all = false) {
		const paths = Object.entries(selected)
			.filter(([, v]) => v)
			.map(([k]) => k);

		const body: any = { force };
		if (all) body.all = true;
		else body.paths = paths;

		const res = await fetch('/api/import/run', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify(body)
		});
		const data = await res.json();
		if (!res.ok) {
			message = data?.error ?? 'Import failed';
			return;
		}
		message = `Imported ${data.rows} row(s) from ${data.files} file(s).`;
		await refresh();
	}

	onMount(refresh);
</script>

<div class="space-y-6">
	<header class="flex flex-col justify-between gap-3 md:flex-row md:items-end">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-white">Imports</h1>
			<p class="mt-1 text-sm text-white/60">
				Import scraper CSVs from <span class="text-white/80">data/results</span>.
			</p>
		</div>
		<div class="flex flex-wrap gap-2">
			<button
				class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
				onclick={refresh}
			>
				Refresh
			</button>
			<a
				class="rounded-xl bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500"
				href="/">Go to Inbox</a
			>
		</div>
	</header>

	{#if message}
		<div class="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/80">
			{message}
		</div>
	{/if}

	<section class="rounded-2xl border border-white/10 bg-white/5 p-4">
		<div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
			<div class="text-sm text-white/70">
				{#if loading}
					Loading…
				{:else}
					{files.length} file(s)
				{/if}
			</div>
			<div class="flex flex-wrap items-center gap-3">
				<label class="flex items-center gap-2 text-sm text-white/70">
					<input type="checkbox" bind:checked={force} class="h-4 w-4 accent-violet-500" />
					Force reimport
				</label>
				<button
					class="rounded-xl bg-violet-600 px-3 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40"
					disabled={!Object.values(selected).some(Boolean)}
					onclick={() => void run(false)}
				>
					Import selected
				</button>
				<button
					class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10"
					onclick={() => void run(true)}
				>
					Import all
				</button>
			</div>
		</div>

		<div class="mt-4 overflow-hidden rounded-xl border border-white/10">
			<table class="w-full text-left text-sm">
				<thead class="bg-black/30 text-xs tracking-wide text-white/60 uppercase">
					<tr>
						<th class="w-10 px-3 py-2"></th>
						<th class="px-3 py-2">File</th>
						<th class="px-3 py-2">Status</th>
						<th class="hidden px-3 py-2 md:table-cell">Size</th>
						<th class="hidden px-3 py-2 lg:table-cell">Modified</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-white/10">
					{#each files as f (f.path)}
						<tr class="hover:bg-white/5">
							<td class="px-3 py-2">
								<input
									type="checkbox"
									class="h-4 w-4 accent-violet-500"
									disabled={f.imported && !force}
									checked={selected[f.path] ?? false}
									onchange={(e) => (selected[f.path] = (e.target as HTMLInputElement).checked)}
								/>
							</td>
							<td class="px-3 py-2 font-medium text-white">{f.name}</td>
							<td class="px-3 py-2 text-white/70">
								{#if f.imported}
									imported
								{:else}
									new
								{/if}
							</td>
							<td class="hidden px-3 py-2 text-white/70 md:table-cell">{humanBytes(f.size)}</td>
							<td class="hidden px-3 py-2 text-white/70 lg:table-cell">
								{new Date(f.mtimeMs).toLocaleString()}
							</td>
						</tr>
					{/each}
					{#if !files.length && !loading}
						<tr>
							<td class="px-3 py-10 text-center text-white/60" colspan="5">No CSVs found.</td>
						</tr>
					{/if}
				</tbody>
			</table>
		</div>
	</section>
</div>
