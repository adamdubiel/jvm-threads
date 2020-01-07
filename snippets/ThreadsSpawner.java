public class ThreadsSpawner {

    private static final int MAX = 5000;

    public static void main(String[] args) {
        for (int i = 0; i < MAX; ++i) {
            Thread thread = new Thread(() -> {
                try {
                    Thread.sleep(100000);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            });
            thread.start();
            i++;
            System.out.println("Spawned " + i + " threads");
        }
    }

}
