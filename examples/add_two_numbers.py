import os
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy
import numpy as np
from keract import get_activations
from tensorflow.keras import Input
from tensorflow.keras.callbacks import Callback
from tensorflow.keras.layers import Dense, Dropout, LSTM, Flatten, Conv1D
from tensorflow.keras.models import load_model, Model
# from tensorflow.python.keras.utils.vis_utils import plot_model
from keras.utils.vis_utils import plot_model

# KERAS_ATTENTION_DEBUG: If set to 1. Will switch to debug mode.
# In debug mode, the class Attention is no longer a Keras layer.
# What it means in practice is that we can have access to the internal values
# of each tensor. If we don't use debug, Keras treats the object
# as a layer and we can only get the final output.

# In this example we need it because we want to extract all the intermediate output values.
os.environ['KERAS_ATTENTION_DEBUG'] = '1'
from attention import Attention


def task_add_two_numbers_after_delimiter(
        n: int, seq_length: int, delimiter: float = 0.0,dim= 1,
        index_1: int = None, index_2: int = None ) -> (np.array, np.array):
    """
    Task: Add the two numbers that come right after the delimiter.
    x = [1, 2, 3, 0, 4, 5, 6, 0, 7, 8]. Result is y = 4 + 7 = 11.
    @param n: number of samples in (x, y).
    @param seq_length: length of the sequence of x.
    @param delimiter: value of the delimiter. Default is 0.0
    @param index_1: index of the number that comes after the first 0.
    @param index_2: index of the number that comes after the second 0.
    @return: returns two numpy.array x and y of shape (n, seq_length, 1) and (n, 1).
    """
    x = np.random.uniform(0, 1, (n, seq_length,dim))
    y = np.zeros(shape=(n, 3))
    print('len(x):',len(x))
    for i in range(len(x)):
        if index_1 is None and index_2 is None:
            a, b = np.random.choice(range(1, len(x[i])), size=2, replace=False)
        else:
            a, b = index_1, index_2

        y[i,0] = 0.5 * x[i, a:a + 1,0] + 0.5 * x[i, b:b + 1,0]
        y[i,1] = 0.25 * x[i, a:a + 1,1] + 0.25 * x[i, b:b + 1,1]
        y[i,2] = 2 * x[i, a:a + 1,0] + 2 * x[i, b:b + 1,0]
        # y[i,1] = 0.5 * x[i, a:a + 1] + 0.5 * x[i, b:b + 1]
        # y[i,2] = 0.5 * x[i, a:a + 1] + 0.5 * x[i, b:b + 1]
        x[i, a - 1:a] = delimiter
        x[i, b - 1:b] = delimiter
    # x = np.expand_dims(x, axis=-1)

    # for n in [0,1]:
    #     print('x')
    #     print(x[n])
    #     print('y')
    #     print(y[n])
    # print(x.shape)
    # print(y.shape)

    # exit()
    return x, y


def main():
    numpy.random.seed(7)
    max_epoch = int(sys.argv[1]) if len(sys.argv) > 1 else 150

    dim =2
    # data. definition of the problem.
    seq_length = 20
    x_train, y_train = task_add_two_numbers_after_delimiter(20_000, seq_length,dim=dim)
    x_val, y_val = task_add_two_numbers_after_delimiter(4_000, seq_length,dim=dim)

    # just arbitrary values. it's for visual purposes. easy to see than random values.
    test_index_1 = 1
    test_index_2 = 19
    x_test, _ = task_add_two_numbers_after_delimiter(n = 5, seq_length = seq_length, delimiter = 0, index_1 = test_index_1, index_2 = test_index_2,dim=dim)
    


    # x_test_mask is just a mask that, if applied to x_test, would still contain the information to solve the problem.
    # we expect the attention map to look like 
    # this mask.
    x_test_mask = np.zeros_like(x_test[..., 0])
    x_test_mask[:, test_index_1:test_index_1 + 1] = 1
    x_test_mask[:, test_index_2:test_index_2 + 1] = 1

    # print('x_test:',x_test)
    # print('x_test:',x_test.shape)
    # exit()
    # Define/compile the model.
    model_input = Input(shape=( seq_length,dim))
    # x = LSTM(100, return_sequences=True, name='encoder_')(model_input)
    x = Conv1D(100,3, padding='same',  name='encoder_')(model_input)
    # x = Flatten()(x)
    # x = Dense(20, use_bias=False, activation='tanh', name='attention_weight') (x)
    x = Attention()(x)
    x = Dropout(0.2)(x)
    x = Flatten()(x)
    x = Dense(20, use_bias=False, activation='tanh' ) (x)
    x = Dense(3, activation='linear')(x)
    model = Model(model_input, x)
    model.compile(loss='mae', optimizer='adam')

    # Visualize the model.
    model.summary()
    plot_model(model,show_dtype=True,show_shapes=True,expand_nested=True,show_layer_activations=True)

    # Will display the activation map in task_add_two_numbers/
    output_dir = Path('task_add_two_numbers')
    if output_dir.exists():
        shutil.rmtree(str(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    class VisualiseAttentionMap(Callback):
        def on_epoch_end(self, epoch, logs=None):
            attention_map = get_activations(model, x_test)['attention_weight_']
            # attention_map = get_activations(model, x_test)['encoder_']
            print("x_test")
            print(x_test.shape)
            # print(x_test)
            print("attention_map")
            print(attention_map.shape)


            # exit()
            # top is attention map, bottom is ground truth.
            plt.imshow(np.concatenate([attention_map, x_test_mask]), cmap='hot')
            plt.colorbar()
            iteration_no = str(epoch).zfill(3)
            plt.axis('off')
            plt.title(f'Iteration {iteration_no} / {max_epoch}')
            output_filename = f'{output_dir}/epoch_{iteration_no}.png'
            print(f'Saving to {output_filename}.')
            plt.savefig(output_filename)
            plt.close()

    # train.
    print('x_train:',x_train.shape)
    print('y_train:',y_train.shape)
    print('x_val:',x_val.shape)
    print('y_val:',y_val.shape)
    model.fit(
        x_train, y_train, validation_data=(x_val, y_val),
        epochs=max_epoch, verbose=2, batch_size=64,
        callbacks=[VisualiseAttentionMap()]
    )

    # test save/reload model.
    pred1 = model.predict(x_val)
    model.save('test_model.h5')
    model_h5 = load_model('test_model.h5')

    # pred2 = model_h5.predict(x_val)
    pred2 = model_h5.predict(x_test)
    
    print("x_test:",x_test)
    print("_:",_)
    print(pred2)

    # np.testing.assert_almost_equal(pred1, pred2)
    print('Success.')


if __name__ == '__main__':
    # pip install pydot
    # pip install keract
    main()
