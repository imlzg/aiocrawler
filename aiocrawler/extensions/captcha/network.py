# coding: utf-8
import numpy as np
from hashlib import sha1
from os import urandom
from typing import Union, Tuple
from typing import List, Iterable
from pathlib import Path
from keras.utils import Sequence
from keras.callbacks import LearningRateScheduler
from keras.layers import Conv2D, BatchNormalization, MaxPooling2D, GRU, Lambda, Input, Flatten
from keras.layers import Reshape, Dense, add, concatenate, Dropout, Activation
from keras.optimizers import Adam
from keras.models import Model
from keras.callbacks import Callback
from keras import backend
from loguru import logger
from string import digits, ascii_letters
from PIL import Image

PathLike = Union[str, Path]


def build_model(width: int,
                height: int,
                rnn_size: int,
                classify_count: int,
                classify_len: int,
                learning_rate: float):
    input_tensor = Input((width, height, 3))
    x = input_tensor
    x = Lambda(lambda a: (a - 127.5) / 127.5)(x)

    for j in range(3):
        for i in range(2):
            x = Conv2D(32 * 2 ** i, (3, 3), kernel_initializer='he_uniform')(x)
            x = BatchNormalization()(x)
            x = Activation('relu')(x)
        x = MaxPooling2D((2, 2))(x)

    conv_shape = x.get_shape().as_list()
    rnn_length = conv_shape[1]
    rnn_dimen = conv_shape[2] * conv_shape[3]
    x = Reshape((rnn_length, rnn_dimen))(x)
    rnn_length -= 2

    x = Dense(rnn_size, kernel_initializer='he_uniform')(x)
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    x = Dropout(0.2)(x)

    gru_1 = GRU(rnn_size, return_sequences=True, kernel_initializer='he_uniform', name='gru1')(x)
    gru_1b = GRU(rnn_size, return_sequences=True, kernel_initializer='he_uniform',
                 go_backwards=True, name='gru1_b')(x)
    x = add([gru_1, gru_1b])

    gru_2 = GRU(rnn_size, return_sequences=True, kernel_initializer='he_uniform', name='gru2')(x)
    gru_2b = GRU(rnn_size, return_sequences=True, kernel_initializer='he_uniform',
                 go_backwards=True, name='gru2_b')(x)
    x = concatenate([gru_2, gru_2b])

    x = Dropout(0.2)(x)
    x = Dense(classify_count, activation='softmax')(x)
    base_model = Model(inputs=input_tensor, outputs=x)

    labels = Input(name='the_labels', shape=[classify_len], dtype='float32')
    input_length = Input(name='input_length', shape=[1], dtype='int64')
    label_length = Input(name='label_length', shape=[1], dtype='int64')
    loss_out = Lambda(ctc_lambda, output_shape=(1,),
                      name='ctc')([x, labels, input_length, label_length])
    opt = Adam(lr=learning_rate)
    ctc_model = Model(inputs=[input_tensor, labels, input_length, label_length], outputs=[loss_out])
    ctc_model.compile(loss={'ctc': lambda y_true, y_pred: y_pred}, optimizer=opt)
    return base_model, ctc_model, rnn_length


def ctc_lambda(args):
    y_pred, labels, input_length, label_length = args
    y_pred = y_pred[:, :, :]
    return backend.ctc_batch_cost(labels, y_pred, input_length, label_length)


def decode_result(y_pred):
    code = None
    if y_pred is not None:
        shape = y_pred[:, :, :].shape
        ctc_decode = backend.ctc_decode(y_pred[:, :, :], input_length=np.ones(shape[0]) * shape[1])
        ctc_decode = ctc_decode[0][0]
        code = backend.get_value(ctc_decode)
    return code


def image_to_numpy_array(img_path: PathLike, width: int = 180, height: int = 80):
    data = Image.open(str(img_path))
    data = data.convert('RGB')
    data = data.resize((width, height, 3), Image.ANTIALIAS)
    return np.array(data).transpose((1, 0, 2))


class Network(object):
    def __init__(self,
                 base_model_path: PathLike = None,
                 ctc_model_path: PathLike = None,
                 width: int = 180,
                 height: int = 80,
                 batch_size: int = 32,
                 classify_len: int = 4,
                 characters: str = None,
                 rnn_size: int = 128,
                 learning_rate: float = 1e-3):

        self._base_model_path = base_model_path
        self._ctc_model_path = ctc_model_path
        self._width = width
        self._height = height
        self._batch_size = batch_size
        self._classify_len = classify_len
        self._characters = characters if characters else '_' + digits + ascii_letters
        self._rnn_size = rnn_size
        self._learning_rate = learning_rate

        self.base_model, self.ctc_model, self.rnn_length = build_model(
            width=self._width,
            height=self._height,
            rnn_size=self._rnn_size,
            classify_count=len(self._characters),
            classify_len=self._classify_len,
            learning_rate=self._learning_rate
        )

    def schedule(self, epoch):
        if epoch % 10 == 0 and epoch != 0:
            lr = backend.get_value(self.ctc_model.optimizer.lr)
            backend.set_value(self.ctc_model.optimizer.lr, lr * 0.6)
        return backend.get_value(self.ctc_model.optimizer.lr)

    def train(self,
              img_path: Iterable[PathLike],
              model_prefix: str = None,
              model_save_path: PathLike = None,
              workers: int = 1,
              epochs: int = 50,
              steps_per_epoch: int = 64,
              train_sample_rate: float = 0.8,
              only_save_weights: bool = True,
              callbacks: List[Callback] = None):

        save_path = Path(model_save_path) if model_save_path else Path()
        model_prefix = model_prefix if model_prefix else sha1(urandom(40)).hexdigest() + '_'

        self._base_model_path = self._base_model_path or save_path / (model_prefix + 'base_model.h5')
        self._ctc_model_path = self._ctc_model_path or save_path / (model_prefix + 'ctc_model.h5')

        handler = ImageHandler(img_path, rate=train_sample_rate)
        train_generator = ImageGenerator(img_data=handler.get_train_samples(),
                                         rnn_length=self.rnn_length,
                                         width=self._width,
                                         height=self._height,
                                         batch_size=self._batch_size,
                                         classify_len=self._classify_len,
                                         characters=self._characters)
        val_generator = ImageGenerator(img_data=handler.get_val_samples(),
                                       rnn_length=self.rnn_length,
                                       width=self._width,
                                       height=self._height,
                                       batch_size=self._batch_size,
                                       classify_len=self._classify_len,
                                       characters=self._characters)

        callbacks = callbacks if callbacks else []
        callbacks.append(ValidationCallback(val_generator, self.base_model))
        callbacks.append(LearningRateScheduler(self.schedule))
        callbacks.append(SaveCallback(only_save_weights,
                                      (self.base_model, self._base_model_path),
                                      (self.ctc_model, self._ctc_model_path)))

        if self._base_model_path and Path(self._base_model_path).is_file():
            self.base_model.load_weights(str(self._base_model_path))

        if self._ctc_model_path and Path(self._ctc_model_path).is_file():
            self.ctc_model.load_weights(str(self._ctc_model_path))

        self.ctc_model.fit_generator(
            generator=train_generator,
            steps_per_epoch=steps_per_epoch,
            use_multiprocessing=True,
            workers=workers,
            epochs=epochs,
            verbose=1,
            callbacks=callbacks,
        )

    def predict(self,
                imgs: List[PathLike],
                base_model_path: PathLike = None):
        if base_model_path and Path(base_model_path).is_file():
            self.base_model.load_weights(str(base_model_path))

        x = np.zeros((len(imgs), self._width, self._height, 3), dtype=np.float32)
        for ix, img in imgs:
            x[ix] = image_to_numpy_array(img)
        y_pred = np.array(self.base_model.predict(x))
        results = decode_result(y_pred)
        results = [''.join([self._characters[ix] for ix in result if ix != 0]) for result in results]
        return results


class ImageHandler(object):
    def __init__(self, img_path: Iterable[PathLike], rate: float = 0.8):
        self.img_type = ['.jpg', '.png', '.jpeg', 'gif']
        self.__img_data = self.load_image_from_path(img_path)
        self._train_len = int(rate * len(self.__img_data))

    def load_image_from_path(self, img_path: Iterable[PathLike], sep: str = '_'):
        img_data = []
        for path in img_path:
            path = Path(path)
            data = [(file.stem.split(sep)[0], file) for file in path.glob('**/*') if file in [self.img_type]]
            img_data.extend(data)
        return img_data

    def get_train_samples(self):
        return self.__img_data[:self._train_len]

    def get_val_samples(self):
        return self.__img_data[self._train_len:-1]


class ImageGenerator(Sequence):
    def __init__(self, img_data: List[Tuple[str, Path]],
                 rnn_length: int,
                 width: int = 180,
                 height: int = 80,
                 batch_size: int = 32,
                 classify_len: int = 4,
                 characters: str = None):
        Sequence.__init__(self)
        self.img_data = img_data
        np.random.shuffle(self.img_data)

        self._rnn_length = rnn_length
        self._width = width
        self._height = height
        self._batch_size = batch_size
        self._classify_len = classify_len
        self._characters = characters if characters else '_' + digits + ascii_letters

    def extend(self, img_data: List[Tuple[str, Path]]):
        self.img_data.extend(img_data)
        np.random.shuffle(self.img_data)

    def __len__(self):
        return len(self.img_data)

    def __getitem__(self, ix):
        x, y = self.load_data(self.img_data[ix * self._batch_size: (ix + 1) * self._batch_size])
        input_length = np.ones(self._batch_size) * self._rnn_length
        label_length = np.ones(self._batch_size) * self._classify_len
        return [x, y, input_length, label_length], np.ones(self._batch_size)

    def load_data(self, img_data: List[Tuple[str, Path]]):
        x = np.zeros((self._batch_size, self._width, self._height, 3), dtype=np.float32)
        y = np.zeros((self._batch_size, self._classify_len), dtype=np.int8)
        for i, (code, img) in enumerate(img_data):
            for ix, ch in enumerate(code[:self._classify_len]):
                y[i][ix] = self._characters.find(ch)

            if img.is_file():
                x[i] = image_to_numpy_array(img, width=self._width, height=self._height)

        return x, y


class ValidationCallback(Callback):
    def __init__(self, generator: ImageGenerator, base_model: Model):
        Callback.__init__(self)
        self._generator = generator
        self._base_model = base_model

    def on_epoch_end(self, epoch, logs=None):
        acc_mean = 0
        for ix in range(self._generator.__len__()):
            [x, y_data, _, _], _ = self._generator.__getitem__(ix)
            y_pred = self._base_model.predict(x)
            shape = y_pred.shape
            decode = backend.ctc_decode(y_pred, input_length=np.ones(shape[0]) * shape[1])[0][0]
            out = backend.get_value(decode)
            acc = 0
            for i, y in enumerate(y_data):
                y = np.array([idx for idx in y if idx != 0])
                pred = out[i][:len(y)]
                if all(pred == y):
                    acc += 1 / len(y_data)
            acc_mean += acc / self._generator.__len__()

        logger.debug('acc: %0.4f%%' % acc_mean)


class SaveCallback(Callback):
    def __init__(self, only_save_weight: bool = True, *models: Tuple[Model, PathLike]):
        Callback.__init__(self)
        self._only_save_weight = only_save_weight
        self._models = models
        self._best = np.inf

    def on_epoch_end(self, _, logs=None):
        current_loss = logs.get('loss', np.inf)
        if current_loss < self._best:
            if self._only_save_weight:
                for model, model_path in self._models:
                    model.save_weights(str(model_path), overwrite=True)
            else:
                for model, model_path in self._models:
                    model.save(str(model_path), overwrite=True)
            logger.debug('Model saved')
