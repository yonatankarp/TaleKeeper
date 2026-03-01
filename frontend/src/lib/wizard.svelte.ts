/** Shared state to open the setup wizard from anywhere. */
let _open = $state(false);

export const wizard = {
  get open() { return _open; },
  show() { _open = true; },
  hide() { _open = false; },
};
