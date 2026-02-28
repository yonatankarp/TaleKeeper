<script lang="ts">
  type Props = {
    size?: string;
  };
  let { size = '24px' }: Props = $props();
</script>

<span class="spinner" style="width: {size}; height: {size}"></span>

<style>
  .spinner {
    display: inline-block;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
