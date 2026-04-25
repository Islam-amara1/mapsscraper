<script lang="ts">
	import './layout.css';
	import { page } from '$app/state';

	let { children } = $props();

	const nav = [
		{ href: '/', label: 'Inbox' },
		{ href: '/callbacks', label: 'Callbacks' },
		{ href: '/interested', label: 'Interested' },
		{ href: '/not-interested', label: 'Not interested' },
		{ href: '/all', label: 'All leads' },
		{ href: '/imports', label: 'Imports' },
		{ href: '/settings', label: 'Settings' }
	] as const;
</script>

<div class="min-h-screen bg-slate-950">
	<div
		class="absolute inset-0 -z-10 bg-[radial-gradient(900px_600px_at_20%_0%,rgba(124,58,237,0.18),transparent_60%),radial-gradient(800px_520px_at_90%_0%,rgba(34,197,94,0.12),transparent_55%)]"
	></div>

	<div class="mx-auto grid max-w-[1400px] grid-cols-12 gap-6 px-4 py-6">
		<aside
			class="col-span-12 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur md:col-span-3 lg:col-span-2"
		>
			<div class="mb-5">
				<div class="text-sm font-semibold tracking-wide text-white">Lead CRM</div>
				<div class="text-xs text-white/60">Local • single user</div>
			</div>

			<nav class="space-y-1">
				{#each nav as item (item.href)}
					<a
						href={item.href}
						class="block rounded-xl px-3 py-2 text-sm transition
							{page.url.pathname === item.href
							? 'bg-white/10 text-white'
							: 'text-white/70 hover:bg-white/7 hover:text-white'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>

			<div class="mt-6 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/70">
				<div class="font-medium text-white">Tip</div>
				<div class="mt-1">
					Import from <span class="text-white/90">data/results</span>, then work your inbox.
				</div>
			</div>
		</aside>

		<main class="col-span-12 md:col-span-9 lg:col-span-10">
			{@render children()}
		</main>
	</div>
</div>
