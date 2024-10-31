document.addEventListener('DOMContentLoaded', function() {
    const cards = document.querySelectorAll('.hoverable-animal-type-cards');
    
    cards.forEach(card => {
        card.addEventListener('mousemove', handleMouseMove);
        card.addEventListener('mouseleave', handleMouseLeave);
        card.addEventListener('mouseenter', handleMouseEnter);
    });

    function handleMouseMove(e) {
        const card = e.currentTarget;
        const cardRect = card.getBoundingClientRect();
        const cardCenterX = cardRect.left + cardRect.width / 2;
        const cardCenterY = cardRect.top + cardRect.height / 2;
        
        const mouseX = e.clientX - cardCenterX;
        const mouseY = e.clientY - cardCenterY;

        const rotateValue = 60;
        
        const rotateX = (mouseY / cardRect.height) * rotateValue;
        const rotateY = -(mouseX / cardRect.width) * rotateValue;
        
        card.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    }

    function handleMouseLeave(e) {
        const card = e.currentTarget;
        card.style.transform = 'rotateX(0) rotateY(0)';
        card.style.border = 'none';
        const h3 = card.querySelector('h3');
        if (h3) {
            h3.style.color = 'white';
        }
    }

    function handleMouseEnter(e) {
        const card = e.currentTarget;
        card.style.border = '3px solid #f4ab0e';
        const h3 = card.querySelector('h3');
        if (h3) {
            h3.style.color = '#f4ab0e';
        }
    }
});