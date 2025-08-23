# ==============================================================================
# Dermatology Prediction Models for BSA, Severity, and Cure Duration
#
# This script contains two separate machine learning models:
# 1. A Convolutional Neural Network (CNN) for image analysis to predict
#    Body Surface Area (BSA) and a general severity score.
# 2. A Gradient Boosting Regressor to predict the 'course duration' or
#    'days to cure' based on structured clinical data.
#
# Each model is self-contained with its own data generation and training loop.
# NOTE: The data used here is randomly generated for demonstration purposes.
# In a real-world scenario, you would replace the dummy data generation
# with your actual, labeled dataset from the Dermosys Web system.
#
# Required Libraries:
# - tensorflow
# - scikit-learn
# - pandas
# - numpy
# You can install them using: pip install tensorflow scikit-learn pandas numpy
# ==============================================================================

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import OneHotEncoder

# --- Model 1: CNN for BSA & Severity Prediction from Images ---

def build_image_prediction_model(input_shape=(128, 128, 3)):
    """
    Builds a simple CNN model for predicting two continuous values: BSA and Severity.
    
    Args:
        input_shape (tuple): The shape of the input images (height, width, channels).
        
    Returns:
        tensorflow.keras.Model: A compiled Keras model.
    """
    model = models.Sequential()
    
    # Convolutional layers to extract features from the image
    model.add(layers.Conv2D(32, (3, 3), activation='relu', input_shape=input_shape))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Conv2D(64, (3, 3), activation='relu'))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Conv2D(128, (3, 3), activation='relu'))
    model.add(layers.MaxPooling2D((2, 2)))
    
    # Flatten the feature map to feed into the dense layers
    model.add(layers.Flatten())
    
    # Dense layers for regression
    model.add(layers.Dense(128, activation='relu'))
    model.add(layers.Dropout(0.5)) # Dropout for regularization
    
    # Output layer with 2 neurons for 2 target values (BSA and Severity)
    # Linear activation is used for regression tasks.
    model.add(layers.Dense(2, activation='linear', name='output_layer'))
    
    # Compile the model
    # We use Mean Squared Error as the loss function, which is standard for regression.
    model.compile(optimizer='adam',
                  loss='mean_squared_error',
                  metrics=['mean_absolute_error'])
    
    return model

def generate_dummy_image_data(num_samples=100, img_size=128):
    """
    Generates a dummy dataset of random images and corresponding BSA/Severity labels.
    In a real project, this is where you would load your actual images and labels.
    """
    # Generate random pixel data for images
    X_images = np.random.rand(num_samples, img_size, img_size, 3)
    
    # Generate random labels for BSA (as a percentage, 0-100) and Severity (e.g., on a 0-10 scale)
    y_bsa = np.random.uniform(1, 50, num_samples)
    y_severity = np.random.uniform(1, 10, num_samples)
    
    # Combine labels into a single array of shape (num_samples, 2)
    y_labels = np.stack([y_bsa, y_severity], axis=1)
    
    return X_images, y_labels

def run_image_model_training():
    """
    Main function to generate data, build, train, and evaluate the image model.
    """
    print("--- Starting CNN Model Training for BSA & Severity Prediction ---")
    
    # 1. Generate Dummy Data
    X_images, y_labels = generate_dummy_image_data(num_samples=500)
    print(f"Generated data shapes: Images={X_images.shape}, Labels={y_labels.shape}")
    
    # 2. Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X_images, y_labels, test_size=0.2, random_state=42)
    
    # 3. Build the CNN model
    image_model = build_image_prediction_model()
    image_model.summary()
    
    # 4. Train the model
    print("\nTraining the image model...")
    # Using a small number of epochs for this demonstration
    history = image_model.fit(X_train, y_train, epochs=10, validation_split=0.1, batch_size=32, verbose=1)
    
    # 5. Evaluate the model on the test set
    print("\nEvaluating the image model...")
    test_loss, test_mae = image_model.evaluate(X_test, y_test, verbose=0)
    print(f"Test Loss (MSE): {test_loss:.4f}")
    print(f"Test Mean Absolute Error: {test_mae:.4f}")
    
    # 6. Make a prediction on a sample image
    print("\nMaking a sample prediction...")
    sample_image = np.expand_dims(X_test[0], axis=0) # Get the first test image and add a batch dimension
    prediction = image_model.predict(sample_image)
    predicted_bsa, predicted_severity = prediction[0]
    actual_bsa, actual_severity = y_test[0]
    
    print(f"Sample Prediction -> Predicted BSA: {predicted_bsa:.2f} | Predicted Severity: {predicted_severity:.2f}")
    print(f"Actual Values   -> Actual BSA:   {actual_bsa:.2f} | Actual Severity:   {actual_severity:.2f}")
    print("--- CNN Model Training Complete ---\n")


# --- Model 2: Gradient Boosting for Cure Duration Prediction ---

def generate_dummy_clinical_data(num_samples=1000):
    """
    Generates a dummy Pandas DataFrame of clinical data.
    In a real project, you would load your patient data from a CSV or database.
    """
    data = {
        'age': np.random.randint(18, 70, num_samples),
        'initial_bsa': np.random.uniform(5, 60, num_samples),
        'initial_severity': np.random.uniform(3, 10, num_samples),
        'comorbidities': np.random.choice([0, 1], num_samples, p=[0.7, 0.3]), # 0: No, 1: Yes
        'medication': np.random.choice(['Med_A', 'Med_B', 'Med_C'], num_samples),
        # The target variable: how many days it took to cure.
        # We'll make it dependent on the other features for a more realistic model.
        'days_to_cure': 100 + (np.random.rand(num_samples) * 30) - ('Med_B' == np.array(['Med_B']*num_samples)) * 20 + ('Med_C' == np.array(['Med_C']*num_samples)) * 15 + (np.random.rand(num_samples) * 20)
    }
    df = pd.DataFrame(data)
    # Simulate medication effect
    df.loc[df['medication'] == 'Med_A', 'days_to_cure'] -= df['initial_bsa'] * 0.5
    df.loc[df['medication'] == 'Med_B', 'days_to_cure'] -= df['initial_bsa'] * 1.2
    df.loc[df['medication'] == 'Med_C', 'days_to_cure'] -= df['initial_bsa'] * 0.8
    df['days_to_cure'] += df['age'] * 0.3
    df['days_to_cure'] = df['days_to_cure'].astype(int).clip(lower=14) # Ensure minimum cure time
    
    return df

def run_clinical_model_training():
    """
    Main function to prepare data, train, and evaluate the clinical data model.
    """
    print("--- Starting Gradient Boosting Model Training for Cure Duration ---")
    
    # 1. Generate Dummy Data
    df = generate_dummy_clinical_data(num_samples=2000)
    print("Generated clinical data sample:")
    print(df.head())
    
    # 2. Define features (X) and target (y)
    X = df.drop('days_to_cure', axis=1)
    y = df['days_to_cure']
    
    # 3. Preprocessing: Handle categorical features
    # We use One-Hot Encoding for the 'medication' column.
    categorical_features = ['medication']
    encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    
    # Fit and transform the categorical features
    encoded_features = encoder.fit_transform(X[categorical_features])
    
    # Create a new DataFrame with the encoded features
    encoded_df = pd.DataFrame(encoded_features, columns=encoder.get_feature_names_out(categorical_features))
    
    # Drop the original categorical column and concatenate the new encoded one
    X = X.drop(categorical_features, axis=1)
    X = pd.concat([X.reset_index(drop=True), encoded_df], axis=1)
    
    print("\nData after one-hot encoding:")
    print(X.head())

    # 4. Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 5. Build and Train the Gradient Boosting Regressor model
    print("\nTraining the Gradient Boosting model...")
    # HistGradientBoostingRegressor is fast and efficient for tabular data.
    gb_model = HistGradientBoostingRegressor(random_state=42)
    gb_model.fit(X_train, y_train)
    
    # 6. Evaluate the model
    print("\nEvaluating the clinical model...")
    y_pred = gb_model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Test Mean Absolute Error: {mae:.2f} days")
    
    # 7. Make a prediction on a sample patient
    print("\nMaking a sample prediction for a new patient...")
    # Create a sample patient profile matching the training data columns
    sample_patient_raw = {
        'age': [45],
        'initial_bsa': [25],
        'initial_severity': [7.5],
        'comorbidities': [1], # Has comorbidities
        'medication': ['Med_B']
    }
    sample_df_raw = pd.DataFrame(sample_patient_raw)

    # Apply the same one-hot encoding
    encoded_sample = encoder.transform(sample_df_raw[categorical_features])
    encoded_sample_df = pd.DataFrame(encoded_sample, columns=encoder.get_feature_names_out(categorical_features))
    sample_df_processed = sample_df_raw.drop(categorical_features, axis=1)
    sample_df_final = pd.concat([sample_df_processed.reset_index(drop=True), encoded_sample_df], axis=1)

    predicted_duration = gb_model.predict(sample_df_final)
    print(f"Patient Profile: {sample_patient_raw}")
    print(f"Predicted Cure Duration: {predicted_duration[0]:.0f} days")
    print("--- Gradient Boosting Model Training Complete ---")


# --- Main Execution Block ---
if __name__ == '__main__':
    # Run the training process for the image model
    run_image_model_training()
    
    print("\n" + "="*60 + "\n")
    
    # Run the training process for the clinical data model
    run_clinical_model_training()
