import { defineConfig, presetWind3, presetWind } from 'unocss';

export default defineConfig({
  content: {
    filesystem: [
      '**/*.{html,js,ts,jsx,tsx,vue,svelte,astro}',
    ],
  },
  presets: [
    presetWind3(),
    presetWind(),
  ],
});
