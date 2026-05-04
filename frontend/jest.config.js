module.exports = {
    testEnvironment: "jsdom",
    reporters: [
        "default",
        ["jest-html-reporter", { outputPath: "test-report.html", pageTitle: "Frontend Unit Tests" }],
        ["jest-junit", { outputDirectory: ".", outputName: "test-report.xml" }]
    ]
};