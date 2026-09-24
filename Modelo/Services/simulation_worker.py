import threading
import queue


class SimulationWorker:

    def __init__(self, simulation):
        self.simulation = simulation

        self.tasks = queue.Queue()
        self.results = queue.Queue()

        self.running = False
        self.thread = None

    def start(self):
        """
        Inicia a thread responsável pela execução da simulação.
        """
        if self.running:
            return

        self.running = True

        self.thread = threading.Thread(
            target=self._worker_loop,
            daemon=True
        )

        self.thread.start()

    def stop(self):
        """
        Solicita a parada do worker.
        """
        self.running = False

    def submit(self, function, *args, **kwargs):
        """
        Envia uma tarefa para ser executada pelo worker.

        Retorna imediatamente e não bloqueia a interface.
        """
        self.tasks.put({
            "function": function,
            "args": args,
            "kwargs": kwargs
        })

    def get_result(self):
        """
        Retorna o próximo resultado disponível.

        Retorna None caso não exista nenhum resultado.
        """
        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None

    def _worker_loop(self):
        """
        Loop interno da thread.
        """
        while self.running:

            try:
                task = self.tasks.get(timeout=0.1)
            except queue.Empty:
                continue

            function = task["function"]
            args = task["args"]
            kwargs = task["kwargs"]

            try:
                result = function(*args, **kwargs)

                self.results.put({
                    "success": True,
                    "result": result,
                    "error": None
                })

            except Exception as error:

                self.results.put({
                    "success": False,
                    "result": None,
                    "error": error
                })

            finally:
                self.tasks.task_done()