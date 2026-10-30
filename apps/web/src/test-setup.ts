import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

// jsdom has no canvas; components that draw must cope with a null context.
HTMLCanvasElement.prototype.getContext = () => null;
