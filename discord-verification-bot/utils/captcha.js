/**
 * Captcha Utility Module
 * Generates and verifies captcha challenges
 */

/**
 * Generate a simple math captcha
 * @returns {Object} Object with question and answer
 */
function generateCaptcha() {
    const types = ['math', 'text'];
    const type = types[Math.floor(Math.random() * types.length)];
    
    if (type === 'math') {
        return generateMathCaptcha();
    } else {
        return generateTextCaptcha();
    }
}

/**
 * Generate a math captcha (addition, subtraction, multiplication)
 * @returns {Object} Object with question and answer
 */
function generateMathCaptcha() {
    const operators = ['+', '-', '*'];
    const operator = operators[Math.floor(Math.random() * operators.length)];
    
    let num1, num2, answer;
    
    switch (operator) {
        case '+':
            num1 = Math.floor(Math.random() * 50) + 1;
            num2 = Math.floor(Math.random() * 50) + 1;
            answer = num1 + num2;
            break;
        case '-':
            num1 = Math.floor(Math.random() * 50) + 10;
            num2 = Math.floor(Math.random() * num1);
            answer = num1 - num2;
            break;
        case '*':
            num1 = Math.floor(Math.random() * 12) + 1;
            num2 = Math.floor(Math.random() * 12) + 1;
            answer = num1 * num2;
            break;
    }
    
    const symbols = { '+': '+', '-': '-', '*': '×' };
    
    return {
        question: `${num1} ${symbols[operator]} ${num2} = ?`,
        answer: answer.toString(),
        type: 'math'
    };
}

/**
 * Generate a text-based captcha
 * @returns {Object} Object with question and answer
 */
function generateTextCaptcha() {
    const challenges = [
        { question: 'What is the color of the sky? (blue/green/red)', answer: 'blue' },
        { question: 'How many days are in a week? (number)', answer: '7' },
        { question: 'What is 2+3? (number)', answer: '5' },
        { question: 'What comes after A in the alphabet?', answer: 'b' },
        { question: 'Type "verify" to continue', answer: 'verify' },
        { question: 'How many fingers on one hand? (number)', answer: '5' },
        { question: 'What is the opposite of hot?', answer: 'cold' },
        { question: 'How many letters in the word "cat"? (number)', answer: '3' },
        { question: 'What is 10 divided by 2? (number)', answer: '5' },
        { question: 'Type the word "human"', answer: 'human' }
    ];
    
    return challenges[Math.floor(Math.random() * challenges.length)];
}

/**
 * Verify captcha answer (case-insensitive)
 * @param {string} userAnswer - User's answer
 * @param {string} correctAnswer - Correct answer
 * @returns {boolean} Whether the answer is correct
 */
function verifyCaptcha(userAnswer, correctAnswer) {
    if (!userAnswer || !correctAnswer) return false;
    
    // Trim and convert to lowercase for comparison
    const cleanUserAnswer = userAnswer.trim().toLowerCase();
    const cleanCorrectAnswer = correctAnswer.toString().trim().toLowerCase();
    
    return cleanUserAnswer === cleanCorrectAnswer;
}

/**
 * Generate an image captcha (requires canvas)
 * This is an advanced feature that creates a visual captcha
 * @returns {Promise<Buffer>} Canvas buffer with captcha image
 */
async function generateImageCaptcha() {
    try {
        const { createCanvas } = require('canvas');
        
        const width = 200;
        const height = 100;
        const canvas = createCanvas(width, height);
        const ctx = canvas.getContext('2d');
        
        // Background
        ctx.fillStyle = '#f0f0f0';
        ctx.fillRect(0, 0, width, height);
        
        // Add noise lines
        for (let i = 0; i < 5; i++) {
            ctx.strokeStyle = `rgb(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255})`;
            ctx.beginPath();
            ctx.moveTo(Math.random() * width, Math.random() * height);
            ctx.lineTo(Math.random() * width, Math.random() * height);
            ctx.stroke();
        }
        
        // Generate random code
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        let code = '';
        for (let i = 0; i < 6; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        
        // Draw text
        ctx.font = '30px Arial';
        ctx.fillStyle = '#333';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Add slight rotation to each character
        for (let i = 0; i < code.length; i++) {
            ctx.save();
            ctx.translate(30 + i * 28, 50);
            ctx.rotate((Math.random() - 0.5) * 0.4);
            ctx.fillText(code[i], 0, 0);
            ctx.restore();
        }
        
        // Add more noise dots
        for (let i = 0; i < 30; i++) {
            ctx.fillStyle = `rgb(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255})`;
            ctx.fillRect(Math.random() * width, Math.random() * height, 2, 2);
        }
        
        return {
            image: canvas.toBuffer('image/png'),
            answer: code
        };
    } catch (error) {
        console.error('Error generating image captcha:', error);
        // Fallback to text captcha
        return generateTextCaptcha();
    }
}

module.exports = {
    generateCaptcha,
    generateMathCaptcha,
    generateTextCaptcha,
    verifyCaptcha,
    generateImageCaptcha
};
