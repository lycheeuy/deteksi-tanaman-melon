/**
 * Deklarasi tipe untuk import file CSS (side-effect import).
 * Menjamin `import "./globals.css"` valid bagi TypeScript di editor
 * mana pun, terlepas dari keberadaan next-env.d.ts maupun versi TS.
 */
declare module "*.css";