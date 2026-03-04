from data import get_mnist
import numpy as np
import cv2

def start_nn():
    # ---------------- ACTIVATIONS ---------------- #

    def relu(x):
        return np.maximum(0, x)

    def relu_deriv(x):
        return (x > 0).astype(float)

    def softmax(x):
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    # ---------------- LOAD DATA ---------------- #

    images, labels = get_mnist()

    # ---------------- INIT WEIGHTS ---------------- #

    w_i_h = np.random.uniform(-0.5, 0.5, (20, 784))
    w_h_o = np.random.uniform(-0.5, 0.5, (10, 20))
    b_i_h = np.zeros((20, 1))
    b_h_o = np.zeros((10, 1))

    learn_rate = 0.01
    epochs = 6

    print("Training started...")

    # ---------------- TRAIN ---------------- #

    for epoch in range(epochs):
        nr_correct = 0

        for img, l in zip(images, labels):
            img = img.reshape(784,1)
            l = l.reshape(10,1)

            # Forward
            h_pre = b_i_h + w_i_h @ img
            h = relu(h_pre)

            o_pre = b_h_o + w_h_o @ h
            o = softmax(o_pre)

            nr_correct += int(np.argmax(o) == np.argmax(l))

            # Backprop
            delta_o = o - l
            old_w_h_o = w_h_o.copy()

            w_h_o -= learn_rate * delta_o @ h.T
            b_h_o -= learn_rate * delta_o

            delta_h = old_w_h_o.T @ delta_o * relu_deriv(h_pre) 
            w_i_h -= learn_rate * delta_h @ img.T
            b_i_h -= learn_rate * delta_h

        acc = round((nr_correct / images.shape[0]) * 100, 2)
        print(f"Epoch {epoch+1} Accuracy: {acc}%")

    print("Training complete.")
    print("Opening camera... Press Q to quit.")  # Q to exit

    # ---------------- CAMERA MODE ---------------- #

    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame,1)

        h_frame, w_frame, _ = frame.shape
        size = 300

        x1 = w_frame//2 - size//2
        y1 = h_frame//2 - size//2
        x2 = x1 + size
        y2 = y1 + size

        cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)

        roi = frame[y1:y2, x1:x2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (28,28))

        # Invert for MNIST style
        resized = cv2.flip(resized,1)
        resized = 255 - resized

        normalized = resized.astype("float32") / 255
        flattened = normalized.reshape(784,1)

        # Forward pass only
        h_pre = b_i_h + w_i_h @ flattened
        h = relu(h_pre)

        o_pre = b_h_o + w_h_o @ h
        o = softmax(o_pre)

        prediction = np.argmax(o)

        cv2.putText(frame, f"Prediction: {prediction}",
                    (40,60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0,255,0),
                    3)

        cv2.imshow("AI Digit Reader", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
if __name__ == "__nn__":
    start_nn()