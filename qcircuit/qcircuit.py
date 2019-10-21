from __future__ import print_function
from jupyter_react import Component
from projectq.ops import X, H, Measure
from projectq.meta import Control
from .constants import Classic, Qureg, Qubit

class QCircuit(Component):
    module = 'QCircuit'

    def __init__(self, **kwargs):
        print('inited')
        #data = [[""], ["X"], ["","","","X","","M"],["","","","","H"],["","Y"]]
        #super(QCircuit, self).__init__(target_name='qcircuit', **kwargs)

        self.qregs = self._generate_qregs(**kwargs)

        super(QCircuit, self).__init__(target_name='qcircuit', props={
            "circuit": [[""]],
            "qregs": self.qregs,
        })
        self.on_msg(self._handle_msg)
        self.current_schema = [None] * len(self._expanded_qregs)

    def _generate_qregs(self, **kwargs):
        qregs = []
        self._expanded_qregs = []

        for name, value in kwargs.items():
            if value == Classic:
                data = {
                    "name": name,
                    "type": "CLASSIC",
                }
                qregs.append(data)
                self._expanded_qregs.append(data)
            elif value == Qubit:
                data = {
                    "name": name,
                    "type": "QUBIT",
                }
                qregs.append(data)
                self._expanded_qregs.append(data)
            else:
                assert isinstance(value, tuple), "Qureg declaration expected as tuple"
                assert len(value) in range(1, 3), "Tuple size error"

                if len(value) == 2:
                    _, size = value
                else:
                    size, = value

                qregs.append({
                    "name": name,
                    "type": "QUREG",
                    "size": size,
                })
                for i in range(size):
                    self._expanded_qregs.append({
                        "name": name,
                        "type": "QUREG",
                        "index": i,
                    })

        return qregs

    def __call__(self, eng, *args, **kwargs):
        self.run(eng, *args, **kwargs)

    def set(self, row, col, gateEncoded):
        self.send({"action": "set_gate", "row": row, "col": col, "gateEncoded": gateEncoded});
		
    def setCircuit(self, circuit):
        self.send({"action": "set_circuit", "circuit": circuit});
		
    def _handle_msg(self, msg):
        self._last_msg = msg
        self.current_schema = msg['content']['data']['qschema']

    def run(self, eng, *args, **kwargs):
        gates = {"X": X, "H": H, "M": Measure}

        name2obj = kwargs
        for i, obj in enumerate(args):
            name2obj[self.qregs[i]["name"]] = obj

        schema_len = 0
        for line in self.current_schema:
            schema_len = max(schema_len, len(line))

        for x in range(schema_len):
            for y, exp_qreg in enumerate(self._expanded_qregs):
                if len(self.current_schema[y]) <= x or self.current_schema[y][x] == "": continue

                encodedGate = self.current_schema[y][x]
                encodedGateT = encodedGate.split('-')
                gate = encodedGateT[0]
                ctrls = encodedGateT[1].split(',') if len(encodedGateT) > 1 else []

                gate_op = gates[gate]

                if exp_qreg['type'] == 'QUREG':
                    op_subject = name2obj[exp_qreg['name']][int(exp_qreg['index'])]
                else:
                    op_subject = name2obj[exp_qreg['name']]

                if not ctrls:
                    gate_op | op_subject
                    print("Debug: ", gate, " | ", exp_qreg['name'])
                else:
                    resolved_ctrls = []
                    for c_index in ctrls:
                        exp_qreg = self._expanded_qregs[int(c_index)]
                        if exp_qreg['type'] == 'QUREG':
                            ctrl_obj = name2obj[exp_qreg['name']][exp_qreg['index']]
                        else:
                            ctrl_obj = name2obj[exp_qreg['name']]

                        resolved_ctrls.append(ctrl_obj)
                    print("Debug: ", gate, " with Control(", ctrls, ")")

                    with Control(eng, *resolved_ctrls):
                        gate_op | op_subject