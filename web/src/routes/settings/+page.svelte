<script lang="ts">
	let confirmText = $state('');
	let msg = $state<string | null>(null);

	async function reset() {
		msg = null;
		const res = await fetch('/api/reset', {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ confirm: confirmText })
		});
		const data = await res.json();
		if (!res.ok) {
			msg = data?.error ?? 'Reset failed';
			return;
		}
		msg = 'Database reset.';
		confirmText = '';
	}
</script>

<div class="space-y-6">
	<header class="flex flex-col justify-between gap-3 md:flex-row md:items-end">
		<div>
			<h1 class="text-2xl font-semibold tracking-tight text-white">Settings</h1>
			<p class="mt-1 text-sm text-white/60">Local-only configuration.</p>
		</div>
	</header>

	{#if msg}
		<div class="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/80">{msg}</div>
	{/if}

	<section class="rounded-2xl border border-white/10 bg-white/5 p-4">
		<h2 class="text-sm font-semibold text-white">Reset database</h2>
		<p class="mt-1 text-sm text-white/60">
			This deletes <code class="rounded bg-black/30 px-1 py-0.5">data/crm.db</code> and recreates it.
		</p>

		<div class="mt-4 flex flex-col gap-3 md:flex-row md:items-center">
			<input
				class="w-full max-w-sm rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white placeholder:text-white/40 focus:ring-2 focus:ring-violet-500/50 focus:outline-none"
				placeholder="Type RESET to confirm"
				bind:value={confirmText}
			/>
			<button
				class="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 hover:bg-white/10 disabled:opacity-40"
				disabled={confirmText !== 'RESET'}
				onclick={() => void reset()}
			>
				Reset
			</button>
		</div>
	</section>
</div>
