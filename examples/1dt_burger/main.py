"""POD-NN modeling for the 1D time-dep Burgers Equation."""

import sys
import os
import yaml
import numpy as np

sys.path.append(os.path.join("..", ".."))
from podnn.podnnmodel import PodnnModel
from podnn.metrics import error_podnn
from podnn.mesh import create_linear_mesh

from datagen import u, generate_test_dataset
from plots import plot_results


def main(hp, gen_test=False, use_cached_dataset=False,
         no_plot=False):
    """Full example to run POD-NN on 1dt_burger."""

    if gen_test:
        generate_test_dataset()

    if not use_cached_dataset:
        # Create linear space mesh
        x_mesh = create_linear_mesh(hp["x_min"], hp["x_max"], hp["n_x"])
        np.save(os.path.join("cache", "x_mesh.npy"), x_mesh)
    else:
        x_mesh = np.load(os.path.join("cache", "x_mesh.npy"))

    # Init the model
    model = PodnnModel("cache", hp["n_v"], x_mesh, hp["n_t"])

    # Generate the dataset from the mesh and params
    X_v_train, v_train, \
        X_v_val, _, \
        U_val = model.generate_dataset(u, hp["mu_min"], hp["mu_max"],
                                       hp["n_s"], hp["train_val_test"],
                                       hp["eps"], eps_init=hp["eps_init"],
                                       t_min=hp["t_min"], t_max=hp["t_max"],
                                       use_cache=use_cached_dataset)
    U_val = model.restruct(U_val)
    U_val_mean = np.mean(U_val, axis=-1)
    U_val_std = np.nanstd(U_val, axis=-1)

    # Create the model and train
    def error_val():
        """Define the error metric for in-training validation."""
        U_val_pred_mean, U_val_pred_std = model.predict_heavy(X_v_val)
        err_mean = error_podnn(U_val_mean, U_val_pred_mean)
        err_std = error_podnn(U_val_std, U_val_pred_std)
        return np.array([err_mean, err_std])
    train_res = model.train(X_v_train, v_train, error_val, hp["h_layers"],
                            hp["epochs"], hp["lr"], hp["lambda"],
                            frequency=hp["log_frequency"])

    # Predict and restruct
    U_pred = model.predict(X_v_val)
    U_pred = model.restruct(U_pred)

    # Sample the new model to generate a HiFi prediction
    n_s_hifi = hp["n_s_hifi"]
    print("Sampling {n_s_hifi} parameters...")
    X_v_val_hifi = model.generate_hifi_inputs(n_s_hifi, hp["mu_min"], hp["mu_max"],
                                              hp["t_min"], hp["t_max"])
    print("Predicting the {n_s_hifi} corresponding solutions...")
    U_pred_hifi_mean, U_pred_hifi_std = model.predict_heavy(X_v_val_hifi)
    U_pred_hifi_mean = U_pred_hifi_mean.reshape((hp["n_x"], hp["n_t"]))
    U_pred_hifi_std = U_pred_hifi_std.reshape((hp["n_x"], hp["n_t"]))

    # Plot against test and save
    return plot_results(U_val, U_pred, U_pred_hifi_mean, U_pred_hifi_std,
                        train_res, hp, no_plot)

if __name__ == "__main__":
    # Custom hyperparameters as command-line arg
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as HPFile:
            HP = yaml.load(HPFile)
    # Default ones
    else:
        from hyperparams import HP

    main(HP, gen_test=False, use_cached_dataset=False)
    # main(HP, gen_test=False, use_cached_dataset=True
