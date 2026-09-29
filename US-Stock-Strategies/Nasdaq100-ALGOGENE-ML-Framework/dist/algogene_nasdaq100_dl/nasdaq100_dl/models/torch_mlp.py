"""Optional PyTorch MLP plugin using the standard framework contract."""

from pathlib import Path

import numpy as np


class Model:
    def __init__(self, hidden_layer_sizes=(128, 64, 32), epochs=40,
                 batch_size=1024, learning_rate=0.001, weight_decay=0.0001,
                 patience=6, random_state=7, device="cpu"):
        self.hidden_layer_sizes = tuple(int(value) for value in hidden_layer_sizes)
        self.epochs = int(epochs)
        self.batch_size = int(batch_size)
        self.learning_rate = float(learning_rate)
        self.weight_decay = float(weight_decay)
        self.patience = int(patience)
        self.random_state = int(random_state)
        self.device_name = str(device)
        self.network = None
        self.mean = None
        self.scale = None

    def _build(self, input_size):
        import torch
        layers = []
        previous = int(input_size)
        for width in self.hidden_layer_sizes:
            layers.extend([torch.nn.Linear(previous, width), torch.nn.ReLU()])
            previous = width
        layers.append(torch.nn.Linear(previous, 1))
        return torch.nn.Sequential(*layers)

    def _normalized(self, features):
        values = np.asarray(features, dtype=np.float32)
        return (values - self.mean) / self.scale

    def fit(self, x_train, y_train, x_validation, y_validation):
        import torch
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)
        device = torch.device(self.device_name)
        x_train = np.asarray(x_train, dtype=np.float32)
        y_train = np.asarray(y_train, dtype=np.float32).reshape(-1, 1)
        x_validation = np.asarray(x_validation, dtype=np.float32)
        y_validation = np.asarray(y_validation, dtype=np.float32).reshape(-1, 1)
        self.mean = x_train.mean(axis=0, keepdims=True)
        self.scale = x_train.std(axis=0, keepdims=True)
        self.scale[self.scale < 1e-8] = 1.0
        train_x = torch.from_numpy(self._normalized(x_train)).to(device)
        train_y = torch.from_numpy(y_train).to(device)
        valid_x = torch.from_numpy(self._normalized(x_validation)).to(device)
        valid_y = torch.from_numpy(y_validation).to(device)
        self.network = self._build(x_train.shape[1]).to(device)
        optimizer = torch.optim.AdamW(
            self.network.parameters(), lr=self.learning_rate,
            weight_decay=self.weight_decay)
        loss_function = torch.nn.MSELoss()
        best_loss, best_state, stale = float("inf"), None, 0
        for _ in range(self.epochs):
            self.network.train()
            order = torch.randperm(len(train_x), device=device)
            for start in range(0, len(order), self.batch_size):
                index = order[start:start + self.batch_size]
                optimizer.zero_grad()
                loss = loss_function(self.network(train_x[index]), train_y[index])
                loss.backward()
                optimizer.step()
            self.network.eval()
            with torch.no_grad():
                validation_loss = float(loss_function(
                    self.network(valid_x), valid_y).cpu()) if len(valid_x) else float(loss.cpu())
            if validation_loss < best_loss - 1e-10:
                best_loss = validation_loss
                best_state = {name: value.detach().cpu().clone()
                              for name, value in self.network.state_dict().items()}
                stale = 0
            else:
                stale += 1
                if stale >= self.patience:
                    break
        if best_state is not None:
            self.network.load_state_dict(best_state)
        self.network = self.network.cpu()
        prediction = self.predict(x_validation) if len(x_validation) else np.array([])
        metrics = {"validation_mse": best_loss, "epochs_ran": self.epochs - max(stale, 0)}
        if len(prediction) and np.std(prediction) and np.std(y_validation):
            metrics["validation_ic"] = float(np.corrcoef(
                prediction, y_validation.reshape(-1))[0, 1])
        return metrics

    def predict(self, features):
        import torch
        if self.network is None:
            raise RuntimeError("model has not been fitted")
        self.network.eval()
        values = torch.from_numpy(self._normalized(features)).float()
        with torch.no_grad():
            return self.network(values).cpu().numpy().reshape(-1)

    def save(self, path: Path):
        import joblib
        path.parent.mkdir(parents=True, exist_ok=True)
        self.network = self.network.cpu()
        joblib.dump(self, path)
