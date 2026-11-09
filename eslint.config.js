/* eslint-disable @typescript-eslint/no-require-imports */
// Configuração do ESLint no formato "flat config" (ESLint 9).
// O objetivo aqui é simples: pegar erro de digitação, variável morta e uso de
// `any` antes do código chegar no pipeline.
const js = require('@eslint/js')
const tseslint = require('typescript-eslint')
const globals = require('globals')

module.exports = tseslint.config(
  {
    ignores: ['dist/**', 'coverage/**', 'node_modules/**'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  {
    // Scripts do k6 rodam em um runtime próprio, onde __ENV é global.
    files: ['k6/**/*.js'],
    languageOptions: {
      globals: {
        __ENV: 'readonly',
      },
    },
  },
)
