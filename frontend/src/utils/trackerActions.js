export const trackerActions = {
  execute(action) {
    return {
      ...action,
      executedAt: new Date().toISOString(),
      status: 'simulated',
    }
  },
}
