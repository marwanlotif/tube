import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library only auto-cleans with test globals enabled; this project imports
// describe/it/expect explicitly, so unmount rendered trees after every test here.
afterEach(() => {
  cleanup();
});
