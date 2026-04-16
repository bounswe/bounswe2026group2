const js = require("@eslint/js");

module.exports = [
    js.configs.recommended,
    {
        ignores: ["android/**", "node_modules/**"],
    },
    {
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "script",
            globals: {
                // Browser globals
                window: "readonly",
                document: "readonly",
                localStorage: "readonly",
                Storage: "readonly",
                fetch: "readonly",
                console: "readonly",
                alert: "readonly",
                FormData: "readonly",
                URLSearchParams: "readonly",
                location: "readonly",
                navigator: "readonly",
                FileReader: "readonly",
                Image: "readonly",
                HTMLElement: "readonly",
                Event: "readonly",
                URL: "readonly",
                // CommonJS exports used by some source files for testing
                module: "readonly",
                // Libraries loaded via <script>
                L: "readonly",
                // Cross-file globals (defined in one file, used in others via <script> tags)
                API_BASE: "writable",
                getToken: "writable",
                saveToken: "writable",
                isLoggedIn: "writable",
                logout: "writable",
                authFetch: "writable",
                requireAuth: "writable",
            },
        },
        rules: {
            "no-unused-vars": ["warn", { args: "none" }],
            "no-undef": "error",
            "no-redeclare": ["error", { builtinGlobals: false }],
        },
    },
    {
        files: ["**/*.test.js", "jest.config.js"],
        languageOptions: {
            sourceType: "commonjs",
            globals: {
                module: "readonly",
                require: "readonly",
                exports: "readonly",
                describe: "readonly",
                test: "readonly",
                expect: "readonly",
                beforeEach: "readonly",
                afterEach: "readonly",
                jest: "readonly",
                global: "readonly",
            },
        },
    },
    {
        files: ["eslint.config.js"],
        languageOptions: {
            sourceType: "commonjs",
            globals: {
                module: "readonly",
                require: "readonly",
            },
        },
    },
    {
        files: ["**/*.mjs"],
        languageOptions: {
            sourceType: "module",
            globals: {
                process: "readonly",
            },
        },
    },
];
