module.exports = {
    testEnvironment: "jsdom",
    testPathIgnorePatterns: ["/node_modules/", "/tests/uat/", "/tests/mobile-e2e/"],
    reporters: [
        "default",
        ["jest-html-reporter", { outputPath: "test-report.html", pageTitle: "Frontend Unit Tests" }],
        ["jest-junit", { outputDirectory: ".", outputName: "test-report.xml" }]
    ]
};
