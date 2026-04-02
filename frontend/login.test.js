const {
    redirectToMap,
    handleLogin,
    handleDemoClick,
    setupLoginForm
} = require("./login");

describe("login page unit tests", () => {
    let assignMock;

    beforeEach(() => {
        document.body.innerHTML = "";
        assignMock = jest.fn();

        delete window.location;
        window.location = {
            assign: assignMock
        };
    });

    test("redirectToMap sends user to map.html", () => {
        redirectToMap();
        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("handleLogin prevents default and redirects", () => {
        const event = {
            preventDefault: jest.fn()
        };

        handleLogin(event);

        expect(event.preventDefault).toHaveBeenCalledTimes(1);
        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("handleDemoClick redirects to map.html", () => {
        handleDemoClick();
        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("setupLoginForm attaches submit listener to form", () => {
        document.body.innerHTML = `
      <form id="login-form">
        <input id="email" type="email" />
        <input id="password" type="password" />
        <button type="submit">Sign In</button>
      </form>
      <button id="demo-button" type="button">Continue to Demo</button>
    `;

        setupLoginForm();

        const form = document.getElementById("login-form");
        const submitEvent = new Event("submit", { bubbles: true, cancelable: true });

        form.dispatchEvent(submitEvent);

        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("setupLoginForm attaches click listener to demo button", () => {
        document.body.innerHTML = `
      <form id="login-form">
        <button type="submit">Sign In</button>
      </form>
      <button id="demo-button" type="button">Continue to Demo</button>
    `;

        setupLoginForm();

        const demoButton = document.getElementById("demo-button");
        demoButton.click();

        expect(assignMock).toHaveBeenCalledWith("map.html");
    });

    test("setupLoginForm does not crash if elements are missing", () => {
        expect(() => setupLoginForm()).not.toThrow();
    });
});