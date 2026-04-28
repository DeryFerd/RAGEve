import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import importPlugin from "eslint-plugin-import";
import jsxA11yPlugin from "eslint-plugin-jsx-a11y";
import nextPlugin from "@next/eslint-plugin-next";
import globals from "globals";

// Recommended rules from each plugin
const reactRecommended = {
  "react/display-name": "off",
  "react/prop-types": "off",
  "react/react-in-jsx-scope": "off",
  "react/no-unknown-property": "off",
  "react/jsx-no-target-blank": "off",
};

const reactHooksRecommended = {
  "react-hooks/exhaustive-deps": "warn",
  "react-hooks/rules-of-hooks": "error",
};

const nextRecommended = {
  ...nextPlugin.configs.recommended.rules,
  "@next/next/no-img-element": "off",
};

const importRecommended = {
  "import/no-anonymous-default-export": "warn",
};

const jsxA11yRecommended = {
  "jsx-a11y/alt-text": ["warn", { elements: ["img"], img: ["Image"] }],
  "jsx-a11y/aria-props": "warn",
  "jsx-a11y/aria-proptypes": "warn",
  "jsx-a11y/aria-unsupported-elements": "warn",
  "jsx-a11y/role-has-required-aria-props": "warn",
  "jsx-a11y/role-supports-aria-props": "warn",
};

export default tseslint.config(
  {
    ignores: [".next/**", "out/**", "build/**", "next-env.d.ts", "node_modules/**"],
  },
  {
    files: ["**/*.{ts,tsx,mts,cts}"],
    extends: [tseslint.configs.recommended],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
        babelOptions: {
          presets: ["next/babel"],
          caller: { supportsTopLevelAwait: true },
        },
      },
    },
    plugins: {
      react: reactPlugin,
      "react-hooks": reactHooksPlugin,
      import: importPlugin,
      "jsx-a11y": jsxA11yPlugin,
      "@next/next": nextPlugin,
    },
    rules: {
      ...reactRecommended,
      ...reactHooksRecommended,
      ...nextRecommended,
      ...importRecommended,
      ...jsxA11yRecommended,
      // Allow unused vars with underscore prefix
      "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
      // Ignore purity and set-state-in-effect rules for now (too strict)
      "react-hooks/purity": "off",
      "react-hooks/set-state-in-effect": "off",
    },
    settings: {
      react: { version: "detect" },
      "import/parsers": {
        "@typescript-eslint/parser": [".ts", ".mts", ".cts", ".tsx", ".d.ts"],
      },
      "import/resolver": {
        node: { extensions: [".js", ".jsx", ".ts", ".tsx"] },
        typescript: { alwaysTryTypes: true },
      },
    },
  }
);
