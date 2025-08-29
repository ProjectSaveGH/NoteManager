import { defineConfig, presetWind3 } from 'unocss';
import presetIcons from '@unocss/preset-icons';

export default defineConfig({
  content: {
    filesystem: [
      '**/*.{html,js,ts,jsx,tsx,vue,svelte,astro}',
    ],
  },
  presets: [
    presetWind3(),
    presetIcons({
      scale: 1.2,
      warn: true,
    }),
  ],
});
