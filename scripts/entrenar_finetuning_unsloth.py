"""
=============================================================================
SEDA - SCRIPT DE FINE-TUNING CON UNSLOTH (QLoRA 4-BIT)
=============================================================================
Este script permite entrenar un modelo de lenguaje (Qwen2.5-Coder-7B o Llama-3-8B)
con el dataset automotriz de SEDA (7,081 ejemplos generados desde SQLite).

Requisitos recomendados para ejecutar:
  - Google Colab con GPU T4 gratuita o GPU local NVIDIA (mínimo 8GB - 16GB VRAM)
  - pip install unsloth "xformers<0.0.29" "trl<0.9.0" peft accelerate bitsandbytes
=============================================================================
"""

import os
from unsloth import FastLanguageModel
import torch
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# 1. Configuración de Parámetros y Modelo Base
max_seq_length = 2048
dtype = None # None para detección automática de Float16 / Bfloat16
load_in_4bit = True # Cuantización a 4-bit con BitsAndBytes (Reduce uso de VRAM a ~6GB)

# Modelos recomendados para Fine-Tuning:
# - "unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit" (Excelente en lógica y reportes)
# - "unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit"
MODEL_NAME = "unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit"

print(f"[SEDA Trainer] Cargando modelo base: {MODEL_NAME}...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=max_seq_length,
    dtype=dtype,
    load_in_4bit=load_in_4bit,
)

# 2. Configuración de Adaptadores LoRA (Parameter-Efficient Fine-Tuning)
model = FastLanguageModel.get_peft_model(
    model,
    r=16, # Rango LoRA (Sugerido 16 o 32)
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0, # 0 optimizado para Unsloth
    bias="none",
    use_gradient_checkpointing="unsloth", # Reduce VRAM drásticamente
    random_state=3407,
)

# 3. Cargar y Formatear el Dataset SEDA
dataset_path = "data/dataset_seda_sft.jsonl"
print(f"[SEDA Trainer] Cargando dataset desde: {dataset_path}...")

dataset = load_dataset("json", data_files=dataset_path, split="train")

def formatting_prompts_func(examples):
    convos = examples["messages"]
    texts = [tokenizer.apply_chat_template(convo, tokenize=False, add_generation_prompt=False) for convo in convos]
    return {"text": texts}

dataset = dataset.map(formatting_prompts_func, batched=True)

# 4. Configuración del Entrenamiento (SFTTrainer)
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    dataset_num_proc=2,
    packing=False, # Puede acelerar secuencias cortas
    args=TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        max_steps=150, # Ajustar a 300 - 500 para entrenamiento completo (~1-2 épocas)
        learning_rate=2e-4,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=10,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir="outputs_seda",
    ),
)

# 5. Ejecutar Entrenamiento
print("[SEDA Trainer] Iniciando entrenamiento con QLoRA...")
trainer_stats = trainer.train()

# 6. Guardar Modelo y Adaptadores LoRA
OUTPUT_DIR = "seda_qwen_lora"
print(f"[SEDA Trainer] Guardando adaptadores LoRA en: {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

# 7. Opcional: Exportar a Formato GGUF para Ollama Local
# Descomentar para exportar directamente:
# model.save_pretrained_gguf("seda_model_gguf", tokenizer, quantization_method="q4_k_m")
print("✅ [SEDA Trainer] ¡Entrenamiento completado exitosamente!")
