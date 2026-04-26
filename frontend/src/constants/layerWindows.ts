// 4 fixed layer windows. Each window is a 6-layer range; each window contains
// 6 layer transitions (2-layer pairs). A transition shows before-cluster,
// after-cluster, and the routes between them.
//
// Mirrored on the backend in `backend/src/api/layer_windows.py`. Values are
// simple enough that drift risk is low; if you change one side, change both.

export const LAYER_WINDOWS = {
  'w0': {
    label: 'Layers 0-5',
    layers: [0, 5],
    transitions: [
      { id: '0-1', layers: [0, 1], label: '0→1' },
      { id: '1-2', layers: [1, 2], label: '1→2' },
      { id: '2-3', layers: [2, 3], label: '2→3' },
      { id: '3-4', layers: [3, 4], label: '3→4' },
      { id: '4-5', layers: [4, 5], label: '4→5' },
      { id: '5-6', layers: [5, 6], label: '5→6' }
    ]
  },
  'w1': {
    label: 'Layers 5-11',
    layers: [5, 11],
    transitions: [
      { id: '5-6', layers: [5, 6], label: '5→6' },
      { id: '6-7', layers: [6, 7], label: '6→7' },
      { id: '7-8', layers: [7, 8], label: '7→8' },
      { id: '8-9', layers: [8, 9], label: '8→9' },
      { id: '9-10', layers: [9, 10], label: '9→10' },
      { id: '10-11', layers: [10, 11], label: '10→11' }
    ]
  },
  'w2': {
    label: 'Layers 11-17',
    layers: [11, 17],
    transitions: [
      { id: '11-12', layers: [11, 12], label: '11→12' },
      { id: '12-13', layers: [12, 13], label: '12→13' },
      { id: '13-14', layers: [13, 14], label: '13→14' },
      { id: '14-15', layers: [14, 15], label: '14→15' },
      { id: '15-16', layers: [15, 16], label: '15→16' },
      { id: '16-17', layers: [16, 17], label: '16→17' }
    ]
  },
  'w3': {
    label: 'Layers 17-23',
    layers: [17, 23],
    transitions: [
      { id: '17-18', layers: [17, 18], label: '17→18' },
      { id: '18-19', layers: [18, 19], label: '18→19' },
      { id: '19-20', layers: [19, 20], label: '19→20' },
      { id: '20-21', layers: [20, 21], label: '20→21' },
      { id: '21-22', layers: [21, 22], label: '21→22' },
      { id: '22-23', layers: [22, 23], label: '22→23' }
    ]
  }
}
